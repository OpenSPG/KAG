import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

logger = logging.getLogger(__name__)


class EvaForHotpotqa:
    """
    init for kag client
    """

    def __init__(self):
        self.resp = SolverPipeline.from_config(KAG_CONFIG.all_config["lf_solver_pipeline"])

    def qa(self, query):
        # CA
        answer, traceLog = self.resp.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, traceLog

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """

    def parallelQaAndEvaluate(
        self, qaFilePath, resFilePath, threadNum=1, upperLimit=10, run_failed=False
    ):
        def process_sample(data):
            try:
                sample_idx, sample = data
                sample_id = sample["_id"]
                question = sample["question"]
                gold = sample["answer"]
                if "prediction" not in sample.keys():
                    prediction, traceLog = self.qa(question)
                else:
                    prediction = sample["prediction"]
                    traceLog = sample["traceLog"]

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

                    if sample_idx % 5 == 0:
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
    import_modules_from_path("./prompt")
    delay_run(hours=0)
    evaObj = EvaForHotpotqa()

    # filePath = "./data/hotpotqa_qa_train.json"
    filePath = "./data/hotpotqa_qa_sub.json"

    start_time = time.time()
    qaFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    resFilePath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"hotpotqa_res_{start_time}.json"
    )
    total_metrics = evaObj.parallelQaAndEvaluate(
        qaFilePath, resFilePath, threadNum=20, upperLimit=100000, run_failed=True
    )

    total_metrics["cost"] = time.time() - start_time
    with open(f"./hotpotqa_metrics_{start_time}.json", "w") as f:
        json.dump(total_metrics, f)
    print(total_metrics)
