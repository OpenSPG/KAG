import os
import json
import asyncio
import logging

from kag.examples.utils import delay_run

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC
from kag.solver.reporter.trace_log_reporter import TraceLogReporter

logger = logging.getLogger(__name__)

from kag.examples.bird_graph.solver.common import load_graph_mschema


class KagBirdQA:
    """
    init for kag client
    """

    async def qa(self, query, db_name="california_schools"):
        reporter: TraceLogReporter = TraceLogReporter()
        resp = SolverPipelineABC.from_config(KAG_CONFIG.all_config["solver_pipeline"])

        answer = await resp.ainvoke(
            query, reporter=reporter, graph_schema=load_graph_mschema(db_name)
        )
        return answer


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    import_modules_from_path("./component")

    evaObj = KagBirdQA()

    # print(asyncio.run(evaObj.qa("What is the highest eligible free rate for K-12 students in the schools in Alameda County?")))
    # print(asyncio.run(evaObj.qa("Please list the lowest three eligible free rates for students aged 5-17 in continuation schools.")))
    # print(asyncio.run(evaObj.qa("Please list the zip code of all the charter schools in Fresno County Office of Education.")))
    # print(asyncio.run(evaObj.qa("What is the unabbreviated mailing street address of the school with the highest FRPM count for K-12 students?")))
    # print(asyncio.run(evaObj.qa("How many test takers are there at the school/s whose mailing city address is in Fresno?")))
    # print(asyncio.run(evaObj.qa("What is the unabbreviated mailing street address of the school with the highest FRPM count for K-12 students?")))
    print(
        asyncio.run(
            evaObj.qa(
                """
                Which school in Contra Costa has the highest number of test takers?
                """.strip()
            )
        )
    )
