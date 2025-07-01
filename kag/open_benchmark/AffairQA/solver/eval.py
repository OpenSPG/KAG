import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate

from kag.interface import SolverPipelineABC
import json
from tqdm import tqdm
import re

logger = logging.getLogger(__name__)


class AffairQaDemo:
    """
    init for kag client
    """

    def qa(self, query, **kwargs):
        resp = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config["kag_solver_pipeline"]
        )
        import asyncio

        answer = asyncio.run(resp.ainvoke(query, **kwargs))

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer

    def parallelQaAndEvaluate(
        self,
        qFilePath,
        aFilePath,
        resFilePath,
        threadNum=1,
        upperLimit=10,
        qids=None,
    ):
        def process_sample(data):
            try:
                sample_idx, sample = data
                sample_id = sample["id"]
                question = sample["question"]
                gold = sample["answer"]
                prediction = self.qa(question, gold=gold)

                evaObj = Evaluate()
                metrics = evaObj.getBenchMark([question], [prediction], gold)
                return sample_idx, sample_id, prediction, metrics
            except Exception as e:
                import traceback

                logger.warning(
                    f"process sample failed with error:{traceback.print_exc()}\nfor: {data} {e}"
                )
                return None

        qList = json.load(open(qFilePath, "r"))
        aList = json.load(open(aFilePath, "r"))
        qaList = []
        for q, a in zip(qList, aList):
            if qids is None:
                qaList.append(
                    {"id": q["id"], "question": q["question"], "answer": a["answer"]}
                )
            elif q["id"] in qids:
                qaList.append(
                    {"id": q["id"], "question": q["question"], "answer": a["answer"]}
                )
        total_metrics = {
            "em": 0.0,
            "f1": 0.0,
            "answer_similarity": 0.0,
            "processNum": 0,
        }
        with ThreadPoolExecutor(max_workers=threadNum) as executor:
            futures = [
                executor.submit(process_sample, (sample_idx, sample))
                for sample_idx, sample in enumerate(
                    qaList if upperLimit <= 0 else qaList[:upperLimit]
                )
            ]
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="parallelQaAndEvaluate completing: ",
            ):
                result = future.result()
                if result is not None:
                    sample_idx, sample_id, prediction, metrics = result
                    sample = qaList[sample_idx]

                    sample["prediction"] = prediction
                    sample["em"] = str(metrics["em"])
                    sample["f1"] = str(metrics["f1"])

                    total_metrics["em"] += metrics["em"]
                    total_metrics["f1"] += metrics["f1"]
                    total_metrics["answer_similarity"] += metrics["answer_similarity"]
                    total_metrics["processNum"] += 1

                    if sample_idx % 50 == 0:
                        with open(resFilePath, "w") as f:
                            json.dump(qaList, f, ensure_ascii=False)

        with open(resFilePath, "w") as f:
            json.dump(qaList, f, ensure_ascii=False)

        res_metrics = {}
        for item_key, item_value in total_metrics.items():
            if item_key != "processNum":
                res_metrics[item_key] = item_value / total_metrics["processNum"]
            else:
                res_metrics[item_key] = total_metrics["processNum"]
        return res_metrics


def get_next_result_filename(base_path):
    """
    Check if result file exists and automatically increment the number.
    Example: if res8.json exists, return res9.json
    """
    dir_path = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)

    # Extract the number from filename (assuming format is res{number}.json)
    match = re.match(r"res(\d+)\.json", base_name)
    if not match:
        return base_path

    current_num = int(match.group(1))

    # Check if file exists, if yes, increment until finding a non-existent filename
    new_num = current_num
    new_path = base_path
    while os.path.exists(new_path):
        new_num += 1
        new_path = os.path.join(dir_path, f"res{new_num}.json")

    logger.info(
        f"Result file incremented from res{current_num}.json to res{new_num}.json"
    )
    return new_path


if __name__ == "__main__":
    dir = os.path.dirname(os.path.abspath(__file__))
    import_modules_from_path(dir)

    demo = AffairQaDemo()

    # query = "胡廷晖是哪里人？"
    # answer, trace_log = demo.qa(query)
    # print(f"Question: {query}")
    # print(f"Answer: {answer}")
    # print(f"TraceLog: {trace_log}")

    dir = os.path.dirname(os.path.abspath(__file__))
    result_file_path = os.path.join(dir, "data/res1.json")
    result_file_path = get_next_result_filename(result_file_path)

    res_metrics = demo.parallelQaAndEvaluate(
        qFilePath=os.path.join(dir, "data/test.json"),
        aFilePath=os.path.join(dir, "data/AffairQA.json"),
        resFilePath=result_file_path,
        threadNum=10,
        upperLimit=-1,
        # qids=['ZJGasStation004'],
        # qids=['ZJGasStation004', 'ZJForestPark031', 'ZJGasStation003', 'ZJGasStation006', 'ZJGasStation007', 'ZJGasStation009', 'ZJForestPark032', 'ZJGasStation023', 'ZJGasStation030', 'ZJGasStation037', 'ZJGasStation033', 'ZJGasStation041', 'ZJGasStation051', 'ZJGasStation044', 'ZJGasStation054', 'ZJHistoricalFigure002', 'ZJHistoricalFigure032', 'ZJMedicalInstitution018', 'ZJMedicalInstitution017', 'ZJMedicalInstitution026', 'ZJMedicalInstitution030', 'ZJMedicalInstitution031', 'ZJMedicalInstitution029', 'ZJNatureReserve005', 'ZJNatureReserve011', 'ZJNatureReserve018', 'ZJNatureReserve022', 'ZJNatureReserve026', 'ZJNatureReserve027', 'ZJNatureReserve037']
    )
    print(res_metrics)
