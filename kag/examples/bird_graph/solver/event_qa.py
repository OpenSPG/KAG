import asyncio
import logging

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)

from kag.examples.bird_graph.solver.common import load_graph_mschema


class EventQA:
    """
    init for kag client
    """

    async def qa(
        self, query, dataset="risk_sentiments_event", db_name="RiskSentimentsEventQA"
    ):
        reporter: TraceLogReporter = TraceLogReporter()
        resp = SolverPipelineABC.from_config(KAG_CONFIG.all_config["solver_pipeline"])
        answer = await resp.ainvoke(
            query,
            reporter=reporter,
            graph_schema=load_graph_mschema(dataset, db_name, "."),
            dataset=dataset,
            db_name="risksentimentseventqa",
        )
        return answer


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./component")
    evaObj = EventQA()

    answer = asyncio.run(
        evaObj.qa(
            """
                为什么泰康人寿厦门分公司被罚35万元?
            """.strip()
        )
    )

    print(answer)
