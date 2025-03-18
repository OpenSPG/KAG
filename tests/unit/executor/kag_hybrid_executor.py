import asyncio
from kag.interface import SolverPipelineABC
from kag.common.conf import KAG_CONFIG
from kag.interface import Task
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_hybrid_executor import KagHybridExecutor

async def qa(pipeline, query):
    result = await pipeline.ainvoke(query)
    return result


def do_pipeline_kag():
    pipeline_config = KAG_CONFIG.all_config["iterative_solver_pipeline"]
    print(f"pipeline_config = {pipeline_config}")
    pipeline = SolverPipelineABC.from_config(pipeline_config)

    query = "周润发的爸爸和妈妈分别叫做什么名字"
    result = asyncio.run(qa(pipeline, query))
    print(result)

def do_kag_hybrid():
    kag_executor = KagHybridExecutor.from_config(KAG_CONFIG.all_config['kag_hybrid_executor'])
    task = Task(executor="kag_hybrid_executor", arguments={
            "query": "周润发的父亲是谁"
        })
    res = kag_executor.invoke(
        query="周润发的父亲是谁",
        task=task,
        context={}
    )
    print(res)

if __name__ == "__main__":
    do_pipeline_kag()