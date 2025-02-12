import logging
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)


class AffairQaDemo:

    """
    init for kag client
    """

    def qa(self, query):
        resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, trace_log = resp.run(query)

        return answer, trace_log

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """


if __name__ == "__main__":
    import_modules_from_path("./prompt")

    demo = AffairQaDemo()
    query = "胡廷晖是哪里人？"
    answer, trace_log = demo.qa(query)
    print(f"Question: {query}")
    print(f"Answer: {answer}")
    print(f"TraceLog: {trace_log}")
