import csv
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from tqdm import tqdm
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.interface import LLMClient
from kag.solver.logic.naive_rag_solver import NaiveRagSolver

from kag.common.checkpointer import CheckpointerManager

logger = logging.getLogger(__name__)


class EvaForAISearch:
    """
    init for kag client
    """

    def __init__(self):
        self.llm_client = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
        pass

    def qa(self, query):
        resp = NaiveRagSolver.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, trace_log = resp.run(query)

        logger.info(f"\nso the answer for '{query}' is: {answer}\n")
        return answer, trace_log

    def load_queries(self, qaFilePath):
        qa_list = []
        with open(qaFilePath, mode='r', newline='', encoding='utf-8') as file1:
            # 使用 csv.reader 读取文件，并指定分隔符为 '\t'
            reader = csv.reader(file1, delimiter='\t')

            # 遍历每一行
            index = 0
            for row in reader:
                index += 1
                qid = row[0]
                query = row[1]
                pid_rels = row[2]

                qa_list.append((qid, query, pid_rels))
        return qa_list

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """

    def parallelQaAndEvaluate(
            self, qaFilePath, resFilePath, threadNum=1, upperLimit=100
    ):
        ckpt = CheckpointerManager.get_checkpointer(
            {"type": "zodb", "ckpt_dir": "ckpt"}
        )

        def process_sample(data):
            try:
                sample_idx, sample = data
                qid, question, pid_rels = sample
                if question in ckpt:
                    print(f"found existing answer to question: {question}")
                    prediction, trace_log = ckpt.read_from_ckpt(question)
                else:
                    prediction, trace_log = self.qa(question)
                    #ckpt.write_to_ckpt(question, (prediction, trace_log))

                evaObj = Evaluate()
                hits, total = evaObj.getAisearchRecallBenchMark(question=question,
                                                                trace_log=trace_log,
                                                                pid_rels=pid_rels)
                return sample_idx, qid, question, pid_rels, prediction, trace_log, hits, total
            except Exception as e:
                import traceback

                logger.warning(
                    f"process sample failed with error:{traceback.print_exc()}\nfor: {data}"
                )
                return None

        qa_list = self.load_queries(qaFilePath)
        res_list = []
        total_metrics = {
            "hits": 0.0,
            "total": 0.0,
        }
        with ThreadPoolExecutor(max_workers=threadNum) as executor:
            futures = [
                executor.submit(process_sample, (sample_idx, sample))
                for sample_idx, sample in enumerate(qa_list[:upperLimit])
            ]
            for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="parallelQaAndEvaluate completing: ",
            ):
                result = future.result()
                if result is not None:
                    sample_idx, qid, query, pid_rels, prediction, traceLog, hits, total = result
                    sample = {}
                    sample['qid'] = qid
                    sample['query'] = query
                    sample['pid#rel'] = pid_rels
                    sample['prediction'] = prediction
                    sample['traceLog'] = traceLog
                    sample['hits'] = hits
                    sample['total'] = total

                    total_metrics["hits"] += float(hits)
                    total_metrics["total"] += float(total)

                    res_list.append(sample)

                    if sample_idx % 50 == 0:
                        with open(resFilePath, "w") as f:
                            json.dump(res_list, f, ensure_ascii=False)

        with open(resFilePath, encoding='utf-8', mode="w") as f:
            json.dump(res_list, f, ensure_ascii=False)

        res_metrics = total_metrics
        res_metrics['recall'] = float(total_metrics['hits']) / float(total_metrics['total'])
        CheckpointerManager.close()
        return res_metrics

    def get_eval(self, recall_ids_list, refs_ids_list):
        """
        :param recall_ids_list: 不同query召回文档id，排序后的结果
            [
                ["23456", "159475", "219110", "567", "453678", "345678", "4353678"],
                ["324567", "34536786", "435367", "34567", "342", "1", "5678"]
            ]
        :param refs_ids_list: 不同query参考的召回的id，下面是两个query的结果，不同query召回的结果和recall_ids_list按下标顺序对齐
            [
                ["159475", "219110", "345675", "23456"],
                ["544453", "692852", "1", "5678", "4325678", "3456"]
            ]
        :return: hit@10, mrr@10, recall@100 对应的指标
        """
        # hit@10, mrr@10, recall@100
        assert len(recall_ids_list) == len(refs_ids_list)
        print('total_query:' + str(len(recall_ids_list)))
        hit_list = []
        mrr_list = []
        recall_metrics_match, recall_metrics_all = 0, 0
        for recall_ids, refs_ids in zip(recall_ids_list, refs_ids_list):

            # 计算hit
            refs_ids_set = set(refs_ids)
            if len(set(recall_ids[:10]) & refs_ids_set) > 0:
                hit_list.append(1)
            else:
                hit_list.append(0)

            # 计算mrr
            mrr_list.append(0.0)
            for idx, r_id in enumerate(recall_ids[:10]):
                if r_id in refs_ids_set:
                    mrr_list[-1] = 1 / float(idx + 1)
                    break

            # recall
            recall_metrics_match += len(set(recall_ids[:10]) & refs_ids_set)
            recall_metrics_all +=  min(10, len(refs_ids_set))


        hit_at_10 = sum(hit_list) / len(hit_list)
        mrr_at_10 = sum(mrr_list) / len(mrr_list)
        recall_at_100 = recall_metrics_match / float(recall_metrics_all)
        print('hitScore:' + str(hit_at_10))
        print('mrrScore:' + str(mrr_at_10))
        print('recallScore:' + str(recall_at_100))
        return hit_at_10, mrr_at_10, recall_at_100


    def eval(self, evalFilePath):
        with open(evalFilePath, 'r') as f:
            content = f.read()  # 全部内容存入字符串
            results = json.loads(content)
            recall_ids_list = []
            refs_ids_list = []
            for res in results:
                if res['qid'] == 'qid':
                    continue
                pid_rel = res['pid#rel']
                refs_list = [element.split("#")[0] for element in pid_rel.split(",")]
                refs_ids_list.append(refs_list)
                traceLogs = res['traceLog']
                recall = []
                for record in  traceLogs:
                    recall.append(record['pid'])
                recall_ids_list.append(recall)
        self.get_eval(recall_ids_list, refs_ids_list)

if __name__ == "__main__":
    import_modules_from_path("./prompt")
    delay_run(hours=0)
    evaObj = EvaForAISearch()
    #answer, traceLog = evaObj.qa("大学怎么网上选宿舍")
    # print(f"answer:{answer}, traceLog:{traceLog}")
    #evaObj.eval("./aisearchqa_res_1742042435.748105.json")
    start_time = time.time()
    filePath = "./data/queries.dev.100.csv"

    qaFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    resFilePath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"aisearchqa_res_{start_time}.json"
    )
    total_metrics = evaObj.parallelQaAndEvaluate(
        qaFilePath, resFilePath, threadNum=5, upperLimit=100
    )

    total_metrics["cost"] = time.time() - start_time
    with open(f"./aisearchqa_metrics_{start_time}.json", encoding='utf-8', mode="w") as f:
        json.dump(total_metrics, f)
    print(total_metrics)

    evaObj.eval(f"./aisearchqa_res_{start_time}.json")
