import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.common.checkpointer import CheckpointerManager

logger = logging.getLogger(__name__)


class EvaFor2wiki:
    """
    init for kag client
    """

    def __init__(self):
        pass

    """
        qa from knowledge base, 
    """

    def qa(self, query):
        resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, traceLog = resp.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, traceLog

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """

    def parallelQaAndEvaluate(
        self, qaFilePath, resFilePath, threadNum=1, upperLimit=10
    ):
        ckpt = CheckpointerManager.get_checkpointer(
            {"type": "zodb", "ckpt_dir": "ckpt"}
        )

        def process_sample(data):
            try:
                sample_idx, sample = data
                sample_id = sample["_id"]
                question = sample["question"]
                gold = sample["answer"]
                if question in ckpt:
                    print(f"found existing answer to question: {question}")
                    prediction, traceLog = ckpt.read_from_ckpt(question)
                else:
                    prediction, traceLog = self.qa(question)
                    ckpt.write_to_ckpt(question, (prediction, traceLog))

                evalObj = Evaluate()
                metrics = evalObj.getBenchMark([prediction], [gold])
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
        CheckpointerManager.close()
        return res_metrics


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    evalObj = EvaFor2wiki()

    start_time = time.time()
    filePath = "./data/2wiki_qa_sub.json"

    evalObj.qa("When did Lothair Ii's mother die?")

    qaFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    resFilePath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"2wiki_res_{start_time}.json"
    )
    total_metrics = evalObj.parallelQaAndEvaluate(
        qaFilePath, resFilePath, threadNum=20, upperLimit=10000
    )

    total_metrics["cost"] = time.time() - start_time
    with open(f"./2wiki_metrics_{start_time}.json", "w") as f:
        json.dump(total_metrics, f)
    print(total_metrics)
