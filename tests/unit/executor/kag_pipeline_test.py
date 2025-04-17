import asyncio

from kag.interface import SolverPipelineABC
from kag.common.conf import KAG_CONFIG
from kag.interface import Task
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KagHybridExecutor,
)
from kag.solver.reporter.open_spg_reporter import OpenSPGReporter

reporter: OpenSPGReporter = OpenSPGReporter(task_id=505)


async def qa(pipeline, query):
    await reporter.start()
    result = await pipeline.ainvoke(query, reporter=reporter)
    await reporter.stop()
    return result


def do_static_pipeline_kag():
    pipeline_config = KAG_CONFIG.all_config["static_solver_pipeline"]
    print(f"pipeline_config = {pipeline_config}")
    pipeline = SolverPipelineABC.from_config(pipeline_config)

    query = "周润发的父亲是做什么工作的"
    result = asyncio.run(qa(pipeline, query))
    print(result)


def do_pipeline_kag():
    pipeline_config = KAG_CONFIG.all_config["iterative_solver_pipeline"]
    print(f"pipeline_config = {pipeline_config}")
    pipeline = SolverPipelineABC.from_config(pipeline_config)

    query = "周润发的爸爸和妈妈叫做什么名字"
    result = asyncio.run(qa(pipeline, query))
    print(result)


def do_kag_hybrid():
    kag_executor = KagHybridExecutor.from_config(
        KAG_CONFIG.all_config["kag_hybrid_executor"]
    )
    task = Task(executor="kag_hybrid_executor", arguments={"query": "周润发的父亲是谁"})
    res = kag_executor.invoke(query="周润发的父亲是谁", task=task, context={})
    print(res)


if __name__ == "__main__":
    do_static_pipeline_kag()
