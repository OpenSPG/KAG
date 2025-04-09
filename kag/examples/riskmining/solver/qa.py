import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.examples.utils import delay_run

from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.interface import SolverPipelineABC

logger = logging.getLogger(__name__)


class EvaQA:
    """
    init for kag client
    """

    def qa(self, query):
        resp = SolverPipelineABC.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, trace_log = resp.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, trace_log

if __name__ == "__main__":
    import_modules_from_path("./prompt")
    delay_run(hours=0)

    evaObj = EvaQA()
    print(evaObj.qa("裘**是否有风险？"))
