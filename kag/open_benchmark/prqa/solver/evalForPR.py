import json
import logging
import os

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.open_benchmark.utils.eval_qa import EvalQa

logger = logging.getLogger()


class PrqaQaDemo(EvalQa):
    """
    init for kag client
    """

    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        super().__init__(task_name="prqa", solver_pipeline_name=solver_pipeline_name)

    def qa(self, query_data, result_file):
        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config[self.solver_pipeline_name]
        )
        for item in query_data:
            question = item.get("question")
            question_id = item.get("id")
            response = pipeline.invoke(query=question)
            self.write_response_to_txt(
                question_id=question_id,
                question=question,
                response=response,
                output_file=result_file,
            )

    @staticmethod
    def write_response_to_txt(question_id, question, response, output_file):
        with open(output_file, "a", encoding="utf-8") as output:
            output.write(f"序号: {question_id}\n")
            output.write(f"问题: {question}\n")
            output.write(f"答案: {response}\n")
            output.write("\n")


if __name__ == "__main__":
    dir_path = os.path.dirname(__file__)
    import_modules_from_path(dir_path)
    data_path = os.path.join(dir_path, "data/test.json")
    qa_result_file = os.path.join(dir_path, "data/result.txt")

    with open(data_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    prqaDemo = PrqaQaDemo()
    prqaDemo.qa(test_data, qa_result_file)
