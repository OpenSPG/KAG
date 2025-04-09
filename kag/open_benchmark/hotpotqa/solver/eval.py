import json
import logging
import os
from typing import List

from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, running_paras, do_main
from kag.common.registry import import_modules_from_path

logger = logging.getLogger(__name__)


class EvaForHotPotQa(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(
            task_name="hotpotqa", solver_pipeline_name=solver_pipeline_name
        )

    def load_data(self, file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    def do_metrics_eval(self, questionList: List[str], predictions: List[str], golds: List[str]):
        eva_obj = Evaluate()
        return eva_obj.getBenchMark(questionList, predictions, golds)


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./executors")
    delay_run(hours=0)
    # 解析命令行参数
    parser = running_paras()
    args = parser.parse_args()
    qa_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), f"{args.qa_file}"
    )
    do_main(
        qa_file_path=qa_file_path,
        thread_num=args.thread_num,
        upper_limit=args.upper_limit,
        collect_file=args.res_file,
        eval_obj=EvaForHotPotQa(),
    )
