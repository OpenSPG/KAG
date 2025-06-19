import asyncio
import logging
from kag.examples.utils import delay_run

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)


class EvaQA:
    """
    init for kag client
    """

    async def qa(self, query):
        reporter: TraceLogReporter = TraceLogReporter()
        resp = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config["kag_solver_pipeline"]
        )
        answer = await resp.ainvoke(query, reporter=reporter)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

        info, status = reporter.generate_report_data()
        logger.info(f"trace log info: {info.to_dict()}")
        return answer


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    delay_run(hours=0)

    evaObj = EvaQA()
    print(asyncio.run(evaObj.qa("裘**是否有风险？")))
