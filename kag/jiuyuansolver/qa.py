import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from kag.common.benchmarks.evaluate import Evaluate
# from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.interface import SolverPipelineABC
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path
from kag.common.checkpointer import CheckpointerManager
import asyncio
logger = logging.getLogger(__name__)

class EvaFor2wiki:
    """
    init for kag client
    """
    def __init__(self):
        pass
    """
        qa from knowledge base,
    """
    def qa(self, query):
        print("读取配置")
        resp = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config["solver_pipeline"]
        )
        # resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])

        print("生成回答")
        answer = asyncio.run(resp.ainvoke(query))
        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer
if __name__ == "__main__":
    # import_modules_from_path("./prompt")
    evalObj = EvaFor2wiki()
    evalObj.qa("中国为什么宣布加强对部分稀土相关物项的出口管制?")
