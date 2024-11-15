import logging
import os

from kag.common.env import init_kag_config
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)


class MedicineDemo:

    """
    init for kag client
    """

    def __init__(self):
        pass

    def qa(self, query):
        # CA
        resp = SolverPipeline()
        answer, trace_log = resp.run(query)

        return answer, trace_log

    """
        parallel qa from knowledge base
        and getBenchmarks(em, f1, answer_similarity)
    """


if __name__ == "__main__":
    demo = MedicineDemo()
    query = "甲状腺结节可以吃什么药？"
    answer, trace_log = demo.qa(query)
    print(f"Question: {query}")
    print(f"Answer: {answer}")
    print(f"TraceLog: {trace_log}")
