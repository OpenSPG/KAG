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


class EvaForMusiqueWithDecomposition(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        self.solver_pipeline_name = solver_pipeline_name
        self.task_name = "musique"

    async def qa(self, query, gold, sub_question_items = None):
        llm = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])

        tmp_res_dict = {}
        result = None
        index = 1
        for sub_question_item in sub_question_items:
            sub_question_idx = sub_question_item["key"]
            sub_question = sub_question_item["value"]["sub_question"]

            sub_question_supporing_paragraph = sub_question_item["value"]["supporing_paragraph"]
            if "#1" in sub_question:
                sub_answer = tmp_res_dict["#1"]
                sub_question = sub_question.replace("#1", sub_answer)
            elif "#2" in sub_question:
                sub_answer = tmp_res_dict["#2"]
                sub_question = sub_question.replace("#2", sub_answer)
            elif "#3" in sub_question:
                sub_answer = tmp_res_dict["#3"]
                sub_question = sub_question.replace("#3", sub_answer)

            promt = f"""
                "Answer the question based on the given reference.Only give me the answer and do not output any other words."
                "\nThe following are given reference:{sub_question_supporing_paragraph} \nQuestion: {sub_question}"
                """

            sub_prediction = llm.__call__(promt)
            key = f"#{index}"
            tmp_res_dict[key] = sub_prediction
            sub_question_item["value"]["sub_prediction"] = sub_prediction
            index += 1
            result = sub_prediction

        trace_log = {"info":{"trace": sub_question_items}}
        return result, trace_log

    def get_supporing_facts(self, sample):
        paragraphs = sample["paragraphs"]
        supporting_facts = {}
        for paragraph in paragraphs:
            if paragraph["is_supporting"] == True:
                idx = paragraph["idx"]
                title = paragraph["title"]
                content = paragraph["paragraph_text"]
                supporting_facts[idx] = f"{title}\n{content}"

        reslist = []
        question_decomposition_list = sample["question_decomposition"]
        index = 0
        for question_decomposition in question_decomposition_list:
            sub_question = question_decomposition["question"]
            sub_answer = question_decomposition["answer"]
            paragraph_support_idx = question_decomposition["paragraph_support_idx"]
            supporing_paragraph = supporting_facts[paragraph_support_idx]

            key = f"#{index}"
            index += 1

            value = {"sub_question":sub_question, "supporing_paragraph": supporing_paragraph, "sub_answer": sub_answer}
            reslist.append({"key":key, "value":value})

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
        eval_obj=EvaForMusiqueWithDecomposition(),
    )
    # obj = EvaForMusique()
    # res = asyncio.run(obj.qa("When did the party that hold the majority in the House of Reps take control of the branch that approves members of the American cabinet?", ""))
