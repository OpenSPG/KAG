import logging
from typing import List

from kag.common.conf import KAG_CONFIG
from kag.interface import SolverPipelineABC
from kag.open_benchmark.utils.eval_qa import EvalQa, do_main
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)


class CsQaEvaluator(EvalQa):
    def __init__(self, solver_pipeline_name="kag_solver_pipeline"):
        self.task_name = "csqa"
        super().__init__(self.task_name, solver_pipeline_name)
        self.solver_pipeline_name = solver_pipeline_name

    def get_question(self, sample):
        return sample["input"]

    def get_answer(self, sample):
        return sample["answers"]

    async def qa(self, query, gold):
        reporter: TraceLogReporter = TraceLogReporter()
        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config[self.solver_pipeline_name]
        )
        answer = await pipeline.ainvoke(query, reporter=reporter, gold=gold)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

        info, status = reporter.generate_report_data()
        return answer, {"info": info.to_dict(), "status": status}

    def load_data(self, file_path):
        import io
        import os
        import json

        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(dir_path, "data")
        file_path = os.path.join(dir_path, "questions.json")
        with io.open(file_path, "r", encoding="utf-8", newline="\n") as fin:
            questions = json.load(fin)
        return questions

    def do_metrics_eval(
        self, questionList: List[str], predictions: List[str], golds: List[str]
    ):
        return {}


def main():
    import os
    from kag.common.registry import import_modules_from_path

    dir_path = os.path.dirname(os.path.abspath(__file__))
    import_modules_from_path(dir_path)

    do_main(
        qa_file_path="",
        thread_num=20,
        upper_limit=5,
        collect_file="benchmark.txt",
        eval_obj=CsQaEvaluator(),
    )


if __name__ == "__main__":
    main()
