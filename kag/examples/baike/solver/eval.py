import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.common.checkpointer import CheckpointerManager


def qa(query):
    resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
    answer, traceLog = resp.run(query)

    print(f"\n\nso the answer for '{query}' is: {answer}\n\n")  #
    print(traceLog)
    return answer, traceLog


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    queries = [
        "周星驰的姓名有何含义？",
        "周星驰和万梓良有什么关系",
        "周星驰在首部自编自导自演的电影中，票房达到多少，他在其中扮演什么角色",
        "周杰伦曾经为哪些自己出演的电影创作主题曲？",
        "周杰伦在春晚上演唱过什么歌曲？是在哪一年",
    ]
    for q in queries:
        qa(q)
