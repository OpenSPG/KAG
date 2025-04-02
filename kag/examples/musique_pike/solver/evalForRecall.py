import json
import logging
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from tqdm import tqdm
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.solver.logic.solver_pipeline import SolverPipeline

from kag.common.checkpointer import CheckpointerManager

logger = logging.getLogger(__name__)


class EvaForMusique:
    """
    init for kag client
    """

    def __init__(self):
        pass

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """

    def generate_id(self, title, content):
        return self.processing_phrases(f"{title}\n{content}").replace("\n", "")

    def convert_chunk_data_2_str(self, predictionlist: list):
        return [processing_phrases(chunk_data["content"]).replace("\n", "") for chunk_data in predictionlist]

    def processing_phrases(self, phrase):
        phrase = str(phrase)
        return re.sub("[^A-Za-z0-9\u4e00-\u9fa5 ]", " ", phrase.lower()).strip()

    def evalForRecall(self, qaFilePath, resFilePath):
        with open(qaFilePath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        final_result = []
        for sample in data:
            results = []
            try:
                subquerys = sample['traceLog']
                count += 1
                for item in subquerys:
                    question = item['sub question']
                for q in item['sub question']:
                    doc_retrieved = q['doc_retrieved']
                    real = []
                    for i in doc_retrieved:
                        real.append(self.processing_phrases(i.split('#')[2]))
                    results.append(self.do_recall_eval(sample,real))
            except Exception as e:
                logger.warning(
                    f"process sample failed with error: {e}"
                )

            all_keys = results[0].keys() if results else []
            max_values = {key: float('-inf') for key in all_keys}
            for obj in results:
                for key in obj:
                    max_values[key] = max(max_values[key], obj[key])
            final_result.append(
                {
                    **sample,
                    "recall":max_values
                }
            )
        total_recall = {"recall_top3": 0, "recall_top5": 0, "recall_all": 0}

        for obj in final_result:
            recall = obj.get("recall", {})
            for param, value in recall.items():
                if param in total_recall:
                    total_recall[param] += value
        for inx, value in  total_recall.items():
            total_recall[inx] = (value*100)/count

        with open(resFilePath, "w") as f:
            json.dump(total_recall, f)

    def do_recall_eval(self, sample, references):
        paragraph_support_idx_set = [idx["paragraph_support_idx"] for idx in sample["question_decomposition"]]
        golds = []
        for idx in paragraph_support_idx_set:
            golds.append(self.generate_id(sample['paragraphs'][idx]['title'], sample['paragraphs'][idx]['paragraph_text']))
        return self.recall_top(predictionlist=references, goldlist=golds)

    def recall_top(self, predictionlist: list, goldlist: List[str]):
        """
               Calculate recall for top-3, top-5, and all predictions.

               Parameters:
               predictionlist (List[str]): List of predicted values from the model.
               goldlist (List[str]): List of actual ground truth values.

               Returns:
               dict: Dictionary containing recall for top-3, top-5, and all predictions.
               """
        # predictionlist = self.convert_chunk_data_2_str(predictionlist)
        # Split predictions into lists of top-3 and top-5
        top3_predictions = predictionlist[:3]
        top5_predictions = predictionlist[:5]

        gold_set = set(goldlist)
        all_set = set(predictionlist)
        top3_set = set(top3_predictions)
        top5_set = set(top5_predictions)

        true_positives_top3 = len(gold_set.intersection(top3_set))
        false_negatives_top3 = len(gold_set - top3_set)

        recall_top3 = true_positives_top3 / (true_positives_top3 + false_negatives_top3) if (
                                                                                                    true_positives_top3 + false_negatives_top3) > 0 else 0.0

        # Update counters for top-5
        true_positives_top5 = len(gold_set.intersection(top5_set))
        false_negatives_top5 = len(gold_set - top5_set)


        recall_top5 = true_positives_top5 / (true_positives_top5 + false_negatives_top5) if (
                                                                                                    true_positives_top5 + false_negatives_top5) > 0 else 0.0
        # Update counters for all
        true_positives_all = len(gold_set.intersection(all_set))
        false_negatives_all = len(gold_set - all_set)

        recall_all = true_positives_all / (true_positives_all + false_negatives_all) if (
                                                                                                true_positives_all + false_negatives_all) > 0 else 0.0

        return {
            "recall_top3": recall_top3,
            "recall_top5": recall_top5,
            "recall_all": recall_all
        }


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    delay_run(hours=0)
    evaObj = EvaForMusique()

    start_time = time.time()
    filePath = "/kag/examples/musique/solver/results/musique_res_1743532848.835058.json"
    # filePath = "./data/musique_qa_train.json"

    qaFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    resFilePath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"musique_res_{start_time}.json"
    )
    evaObj.evalForRecall(qaFilePath, resFilePath)


