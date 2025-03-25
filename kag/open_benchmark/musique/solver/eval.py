import asyncio
import json
import logging
import os
from typing import List

from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, do_main, running_paras

logger = logging.getLogger(__name__)


class EvaForMusique(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(task_name="musique", solver_pipeline_name=solver_pipeline_name)

    def load_data(self, file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    def do_recall_eval(self, sample, references):
        eva_obj = Evaluate()
        paragraph_support_idx_set = [idx["paragraph_support_idx"] for idx in sample["question_decomposition"]]
        golds = []
        for idx in paragraph_support_idx_set:
            golds.append(eva_obj.generate_id(sample['paragraphs'][idx]['title'], sample['paragraphs'][idx]['paragraph_text']))
        return eva_obj.recall_top(predictionlist=references, goldlist=golds)

    def do_metrics_eval(self, predictions: List[str], golds: List[str]):
        eva_obj = Evaluate()
        return eva_obj.getBenchMark(predictions, golds)


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    delay_run(hours=0)
    # 解析命令行参数
    parser = running_paras()
    args = parser.parse_args()
    qa_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), f"{args.qa_file}")
    do_main(qa_file_path=qa_file_path, thread_num=args.thread_num, upper_limit=args.upper_limit,
            collect_file=args.res_file, eval_obj=EvaForMusique())
