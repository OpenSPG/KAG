import asyncio
import logging
from kag.common.conf import KAG_CONFIG
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger()


async def qa(query):
    reporter: TraceLogReporter = TraceLogReporter()
    resp = SolverPipelineABC.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
    answer = await resp.ainvoke(query, reporter=reporter)

    logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")

    info, status = reporter.generate_report_data()
    logger.info(f"trace log info: {info.to_dict()}")
    return answer


if __name__ == "__main__":
    queries = [
        "皮质激素有什么作用",
    ]
    for q in queries:
        print(asyncio.run(qa(q)))
