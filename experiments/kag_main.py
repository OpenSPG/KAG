#

import json
import logging
import os
import sys
import time
import argparse
from copy import deepcopy
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from kag.builder.component.writer import KGWriter
from kag.builder.default_chain import KAGBuilderChain
from kag.common.benchmarks.evaluate import Evaluate
from kag.common.env import init_kag_config
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.solver.solver_pipeline import LogicalFormSolver
from kag.solver.resp_solver import ReSPPipeline
from kag.solver.ir_cot_solver import IRCoTPipeline


from experiments.exp_data_reader import PreExtractedSubGraph


logger = logging.getLogger(__name__)
neo4j_logger = logging.getLogger("neo4j.notifications")
neo4j_logger.setLevel(logging.ERROR)


class ExperimentBuildChain(KAGBuilderChain):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.with_sim_edge = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_SIM_EDGE"))
        self.with_entity_norm = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_ENTITY_NORM"))
        self.with_hyper_expand = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_HYPER_EXPAND"))

    def get_dag(self, suffix=''):
        source = PreExtractedSubGraph(
            self.with_sim_edge, self.with_entity_norm, self.with_hyper_expand
        )
        sink = KGWriter()
        chain = source >> sink
        return chain.dag


class FastSetting:

    default_config = {
        "graph_store": {
            "uri": "neo4j://localhost:7687",
            "user": "",
            "password": "",
        },
        "vectorizer": {
            "vectorizer": "knext.common.vectorizer.LocalVectorizer",
            "path": "~/.cache/vectorizer/BAAI/bge-base-en-v1.5",
        },
        "llm": {},
        "retriever": {},
        "experiment": {},
        "log": {"kag_log_level": "INFO"}
    }

    # graph name to (nro4j) db name
    _gname2db = {
        "2wiki_deepseek": "tc.neo4j.fi11",
    }

    # QA dataset file
    _dname2qa_file = {
        "2wiki": "./dataset/2wikimultihopqa.json",
    }

    _retriever_setting = {
        "SR": {  # Full Semantic Enhance Retriever
            "pagerank_threshold": 0.9,
            "match_threshold": 0.8,
            "top_k": 10,
            "with_semantic_fix_onto": True,
            "with_semantic_entity_norm": True,
            "with_semantic_hyper_expand": True,
            "force_chunk_retriever": False,
            "max_semantic_expand": 3,
            "semantic_synonym_threshold": 0.9,
            "max_run": 3,
        },
        "SRC": {  # Force Chunk Semantic Enhance Retriever
            "pagerank_threshold": 0.9,
            "match_threshold": 0.8,
            "top_k": 10,
            "with_semantic_fix_onto": True,
            "with_semantic_entity_norm": True,
            "with_semantic_hyper_expand": True,
            "force_chunk_retriever": True,
            "max_semantic_expand": 3,
            "semantic_synonym_threshold": 0.9,
            "max_run": 3,
        },
        "NSR": {  # Non-Semantic Enhance Retriever
            "pagerank_threshold": 0.9,
            "match_threshold": 0.8,
            "top_k": 10,
            "with_semantic_fix_onto": False,
            "with_semantic_entity_norm": False,
            "with_semantic_hyper_expand": False,
            "force_chunk_retriever": True,
            "max_run": 3,
        },
    }

    _qa_method = {
        'LF': "qa_lf",   # QA with Logical Form
        "Resp": "qa_resp",   # QA with Natural Language query decompose
        "IRCoT": 'qa_ir_cot'  # QA with IRCoT
    }

    _llm_config = {
        "gpt35": {
        },
        "deepseek": {
        }
    }

    def __init__(self, dataset_name, graph_name, qa_method, retriever_type, save_dir):
        self.save_dir = save_dir  # 推理结果保存路径
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        self.dataset_file = self._dname2qa_file[dataset_name]
        self.graph_db_name = self._gname2db[graph_name]
        self.qa_method = self._qa_method[qa_method]
        self.retriever_params = self._retriever_setting[retriever_type]
        if 'gpt35' in graph_name:
            self.llm_config = self._llm_config['gpt35']
        elif 'deepseek' in graph_name or 'dpsk' in graph_name:
            self.llm_config = self._llm_config['deepseek']
        else:
            raise ValueError("no llm type in graph_name: {} ".format(graph_name))
        self.name = '_'.join([dataset_name, graph_name, qa_method, retriever_type])
        self.config = deepcopy(self.default_config)

    def write(self, save_dir):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        to_file = os.path.join(save_dir, f"{self.name}.cfg")
        wf = open(to_file, 'w')
        for name, detail in self.config.items():
            wf.write(f"[{name}]\n")
            for k, v in detail.items():
                wf.write(f"{k} = {v}\n")
            wf.write('\n')
        wf.close()
        return to_file

    def setup_config(self):
        self.config["graph_store"]["database"] = self.graph_db_name
        self.config["llm"].update(self.llm_config)
        self.config["retriever"].update(self.retriever_params)
        file_name = self.dataset_file.split('/')[-1]
        _save_file = os.path.join(self.save_dir, file_name)
        self.config["experiment"] = {
            "qa_method": self.qa_method,
            "qa_file": self.dataset_file,
            "pred_save_file": _save_file.replace(".json", f"_{self.name}_res.json"),
            "metrics_save_file": _save_file.replace(".json", f"_{self.name}_metrics.json"),
        }


class Experiment:

    """
    init for kag client
    """

    def __init__(self, config_file_path):
        self.configFilePath = config_file_path
        init_kag_config(self.configFilePath)
        resume_from = os.getenv("KAG_INDEXER_RESUME_FROM")
        if resume_from:
            self.builder_class = ExperimentBuildChain
        else:
            self.builder_class = KAGBuilderChain

    def build_kb(self, corpus_file_path, **kwargs):
        self.builder_class().invoke(corpus_file_path, **kwargs)
        logger.info(f"\n\nbuildKB successfully for {corpus_file_path}\n\n")

    def reset_all_graph(self):
        graph_store = Neo4jClient(
            uri=os.getenv("KAG_GRAPH_STORE_URI"),
            user=os.getenv("KAG_GRAPH_STORE_USER"),
            password=os.getenv("KAG_GRAPH_STORE_PASSWORD"),
            database=os.getenv("KAG_GRAPH_STORE_DATABASE"),
        )
        graph_store._update_pagerank_graph()

    def qa_lf(self, query, **kwargs):
        pipeline = LogicalFormSolver(**kwargs)
        answer, trace_log = pipeline.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

    def qa_resp(self, query, **kwargs):
        pipeline = ReSPPipeline(**kwargs)
        answer, trace_log = pipeline.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

    def qa_ir_cot(self, query, **kwargs):
        pipeline = IRCoTPipeline(**kwargs)
        answer, trace_log = pipeline.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

    def run_experiment(
        self, qaFilePath, resFilePath, threadNum=1, upperLimit=10
    ):

        """
            parallel qa from knowledge base
            and getBenchmarks(em, f1, answer_similarity)
        """
        qa_func = getattr(self, os.getenv("KAG_EXPERIMENT_QA_METHOD"))
        qa_params = {}
        if os.getenv("KAG_EXPERIMENT_QA_METHOD") == 'qa_ir_cot':
            f_name = qaFilePath.split('/')[-1]
            if '2wiki' in f_name:
                qa_params['dataset_name'] = '2wiki'
            elif 'hotpotqa' in f_name:
                qa_params['dataset_name'] = 'hotpotqa'
            elif 'musique' in f_name:
                qa_params['dataset_name'] = 'musique'
            else:
                raise ValueError(f"invalid dataset name: {f_name}")

        logger.info(f"using qa method: {qa_func.__name__}")

        def process_sample(data):
            try:
                sample_idx, sample = data
                sample_id = sample.get("id") or sample.get("_id")
                question = sample["question"]
                gold = sample["answer"]
                prediction, traceLog = qa_func(question, **qa_params)

                evaObj = Evaluate()
                metrics = evaObj.get_bench_mark([prediction], [gold])
                return sample_idx, sample_id, prediction, metrics, traceLog
            except Exception as e:
                import traceback

                logger.warning(
                    f"process sample failed with error:{traceback.print_exc()}\nfor: {data}"
                )
                return None

        # reset neo4j all_graph before qa
        self.reset_all_graph()
        qaList = json.load(open(qaFilePath, "r"))
        total_metrics = {
            "em": 0.0,
            "f1": 0.0,
            "answer_similarity": 0.0,
            "processNum": 0,
        }
        with ThreadPoolExecutor(max_workers=threadNum) as executor:
            futures = [
                executor.submit(process_sample, (sample_idx, sample))
                for sample_idx, sample in enumerate(qaList[:upperLimit])
            ]
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="parallelQaAndEvaluate completing: ",
            ):
                result = future.result()
                if result is not None:
                    sample_idx, sample_id, prediction, metrics, traceLog = result
                    sample = qaList[sample_idx]

                    sample["prediction"] = prediction
                    sample["traceLog"] = traceLog
                    sample["em"] = str(metrics["em"])
                    sample["f1"] = str(metrics["f1"])

                    total_metrics["em"] += metrics["em"]
                    total_metrics["f1"] += metrics["f1"]
                    total_metrics["answer_similarity"] += metrics["answer_similarity"]
                    total_metrics["processNum"] += 1

                    if sample_idx % 50 == 0:
                        with open(resFilePath, "w") as f:
                            json.dump(qaList, f)

        with open(resFilePath, "w") as f:
            json.dump(qaList, f)

        res_metrics = {}
        for item_key, item_value in total_metrics.items():
            if item_key != "processNum":
                res_metrics[item_key] = item_value / total_metrics["processNum"]
            else:
                res_metrics[item_key] = total_metrics["processNum"]
        return res_metrics


if __name__ == "__main__":

    DEBUG = False
    if DEBUG:
        sys.argv.extend(["qa", "-c", "default.cfg"])

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', help='KAG')

    # build
    parser_build = subparsers.add_parser('build', help='Semantic Graph Indexing')
    parser_build.add_argument(
        "--config", "-c", type=str, default=None,
        help="config file path for index building task."
    )
    parser_build.add_argument(
        '--dataset', '-d', type=str,
        help='dataset name, used to generate config file and then in QA experiments.'
    )

    # qa
    parser_qa = subparsers.add_parser('qa', help='Retrieval And Generation')
    parser_qa.add_argument(
        '--config', '-c', type=str, default=None,
        help='config file, when specified, use this config file directly and ignores other arguments.'
    )
    parser_qa.add_argument(
        '--dataset', '-d', type=str,
        help='dataset name, used to generate config file and then in QA experiments.'
    )
    parser_qa.add_argument(
        '--graph', '-g', type=str,
        help='graph name, used to generate config file and then in QA experiments.'
    )
    parser_qa.add_argument(
        '--qa_method', '-m', type=str,
        help='QA method, `qa_lf`, `qa_resp` or `qa_ir_cot`. used to generate config file and then in QA experiments.'
    )
    parser_qa.add_argument(
        '--retriever', '-r', type=str,
        help=('retriever name, `LF` for Logic Form or `Resp` for Entity retrieval. '
              'used to generate config file and then in QA experiments.')
    )
    parser_qa.add_argument(
        '--save_res', '-s', type=str, default="./results",
        help='result save directory. Default: "./results"'
    )
    parser_qa.add_argument(
        '--save_config', type=str, default="./configs/qa/",
        help='config file save directory. Default current directory.'
    )
    args = parser.parse_args()

    if args.command == 'build':
        print("Running Graph Building Task")
        pwd = os.path.abspath(os.path.dirname(__file__))
        configFilePath = os.path.join(pwd, f"configs/{args.config}")
        experiment = Experiment(config_file_path=configFilePath)
        corpusFilePath = os.getenv("KAG_INDEXER_CORPUS_PATH")
        experiment.build_kb(corpusFilePath, max_workers=1 if DEBUG else 30)

    elif args.command == 'qa':
        print("Running QA Task")
        # prepare config file
        if args.config is not None:
            config_file = args.config
        else:
            setting = FastSetting(args.dataset, args.graph, args.qa_method, args.retriever, args.save_res)
            setting.setup_config()
            config_file = setting.write(args.save_config)
        experiment = Experiment(config_file_path=config_file)
        start_time = time.time()
        qaFilePath = os.getenv("KAG_EXPERIMENT_QA_FILE")
        resFilePath = os.getenv("KAG_EXPERIMENT_PRED_SAVE_FILE")
        total_metrics = experiment.run_experiment(
            qaFilePath, resFilePath, threadNum=1 if DEBUG else 20, upperLimit=(100 if DEBUG else 10000)
        )
        total_metrics['cost'] = time.time() - start_time
        with open(os.getenv("KAG_EXPERIMENT_METRICS_SAVE_FILE"), "w") as f:
            json.dump(total_metrics, f)
        print(total_metrics)

    else:
        parser.print_help()
