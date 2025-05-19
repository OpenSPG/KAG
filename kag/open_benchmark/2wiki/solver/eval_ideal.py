import json
import logging
import os
import random
from typing import List

from kag.common.conf import KAG_CONFIG
from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run
from kag.open_benchmark.utils.eval_qa import EvalQa, running_paras, do_main
from kag.common.registry import import_modules_from_path
from kag.interface import LLMClient

logger = logging.getLogger(__name__)


class EvaFor2wiki(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(
            task_name="2wiki", solver_pipeline_name=solver_pipeline_name
        )

    def load_data(self, file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    async def qa(self, query, gold, supporting_facts = None, sample = None):
        llm = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])

        prompt = """Check the relevance of given references.\n"""
        prompt += """Give me the item ids of the references as a JSON array that are relevant to the question.\n"""
        prompt += """You should omit the reasoning process, just give me the item ids."""
        prompt += "\n\nThe following are given references:"
        for i, item in enumerate(supporting_facts, 1):
            prompt += "\n{}. {}".format(i, item)
        prompt += "\n\nQuestion: {}".format(query)

        result = await llm.acall(prompt)
        try:
            item_ids = json.loads(result)
            supporting_facts = [supporting_facts[i - 1] for i in item_ids]
        except Exception:
            return "noanswer", {"info":{"prompt": prompt, "tag": "LLM_FILTER_FAILED", "result": result}}

        not_filtered = []
        is_supporting = set(x[0] for x in sample["supporting_facts"])
        # for item in supporting_facts:
        #     if item["title"] not in is_supporting:
        #         not_filtered.append(item)

        prompt = f"""
            "Answer the question based on the given reference.Only give me the answer and do not output any other words."
            "\nThe following are given reference:{supporting_facts} \nQuestion: {query}"
            """

        result = await llm.acall(prompt)
        trace_log = {"info":{"prompt": prompt, "tag": "LLM_FILTER_SUCCESS", "filtered_supporting_facts": supporting_facts, "result": result}}
        return result, trace_log

    def get_supporing_facts(self, sample):
        paragraphs = sample["context"]
        is_supporting = set(x[0] for x in sample["supporting_facts"])
        supporing_facts = []
        non_supporting_facts= []
        for paragraph in paragraphs:
            doc = {
                "title": paragraph[0],
                "content": " ".join(paragraph[1]),
            }
            if doc["title"] in is_supporting:
                supporing_facts.append(doc)
            else:
                non_supporting_facts.append(doc)
        if 1:
            reslist = non_supporting_facts[:10]
            reslist.extend(supporing_facts)
            random.shuffle(reslist)
        else:
            reslist = []
            reslist.extend(supporing_facts)
            #reslist.extend(non_supporting_facts[:10])
        return reslist

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
        eval_obj=EvaFor2wiki(),
    )
