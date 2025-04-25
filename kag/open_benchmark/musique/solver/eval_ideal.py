import json
import logging
import os
from typing import List

from kag.interface import SolverPipelineABC
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, do_main, running_paras
from kag.solver.reporter.trace_log_reporter import TraceLogReporter
from kag.interface import LLMClient
import random
logger = logging.getLogger(__name__)


class EvaForMusique(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        self.solver_pipeline_name = solver_pipeline_name
        self.task_name = "musique"

    async def qa(self, query, supporting_facts, gold):
        promt = f"""
            "Answer the question based on the given reference.Only give me the answer and do not output any other words."
            "\nThe following are given reference:{supporting_facts} \nQuestion: {query}"
            """

        llm = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
        result = llm.__call__(promt)
        trace_log = {"info":{"prompt": promt}}
        return result, trace_log

    def get_supporing_facts(self, sample):
        paragraphs = sample["paragraphs"]
        supporing_facts = []
        non_supporting_facts= []
        for paragraph in paragraphs:
            if paragraph["is_supporting"] == True:
                supporing_facts.append({"title":paragraph["title"], "content":paragraph["paragraph_text"]})
            else:
                non_supporting_facts.append({"title":paragraph["title"], "content":paragraph["paragraph_text"]})

        reslist = non_supporting_facts[:10]
        reslist.extend(supporing_facts)
        random.shuffle(reslist)
        return reslist

    def load_data(self, file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    def do_recall_eval(self, sample, references):
        eva_obj = Evaluate()
        paragraph_support_idx_set = [
            idx["paragraph_support_idx"] for idx in sample["question_decomposition"]
        ]
        golds = []
        for idx in paragraph_support_idx_set:
            golds.append(
                eva_obj.generate_id(
                    sample["paragraphs"][idx]["title"],
                    sample["paragraphs"][idx]["paragraph_text"],
                )
            )
        return eva_obj.recall_top(predictionlist=references, goldlist=golds)

    def do_metrics_eval(
        self, questionList: List[str], predictions: List[str], golds: List[str]
    ):
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
        eval_obj=EvaForMusique(),
    )
    # obj = EvaForMusique()
    # res = asyncio.run(obj.qa("When did the party that hold the majority in the House of Reps take control of the branch that approves members of the American cabinet?", ""))
