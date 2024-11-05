import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.common.env import init_kag_config
from kag.examples.utils import delay_run
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from knext.reasoner.client import ReasonerClient
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)


class SupplyChainDemo:
    """
    init for kag client
    """

    def __init__(self, configFilePath):
        self.configFilePath = configFilePath
        init_kag_config(self.configFilePath)

    def qa(self, query):
        resp = SolverPipeline()
        answer, trace_log = resp.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

    def qaWithoutLogicForm(self, query):
        # CA
        lf_solver = LFSolver(
            chunk_retriever=LFChunkRetriever(), kg_retriever=KGRetrieverByLlm()
        )
        reasoner = DefaultReasoner(lf_planner=LFPlannerABC(), lf_solver=lf_solver)
        resp = SolverPipeline(reasoner=reasoner)
        answer, trace_log = resp.run(query)
        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """

    def parallelQaAndEvaluate(
        self, qaFilePath, resFilePath, threadNum=1, upperLimit=10
    ):
        def process_sample(data):
            try:
                sample_idx, sample = data
                sample_id = sample["id"]
                question = sample["question"]
                gold = sample["answer"]
                prediction, traceLog = self.qa(question)

                evaObj = Evaluate()
                metrics = evaObj.getBenchMark([prediction], [gold])
                return sample_idx, sample_id, prediction, metrics, traceLog
            except Exception as e:
                import traceback

                logger.warning(
                    f"process sample failed with error:{traceback.print_exc()}\nfor: {data}"
                )
                return None

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

    delay_run(hours=0)
    configFilePath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "../kag_config.cfg"
    )
    demo = SupplyChainDemo(configFilePath=configFilePath)
    print(demo.qa("顺丁橡胶成本上涨对那些公司产生了影响"))
