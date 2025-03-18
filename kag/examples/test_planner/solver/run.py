# -*- coding: utf-8 -*-
import asyncio
from kag.interface import SolverPipelineABC
from kag.common.conf import KAG_CONFIG


async def qa(pipeline, query):
    result = await pipeline.ainvoke(query, )
    return result


if __name__ == "__main__":
    pipeline_config = KAG_CONFIG.all_config["static_solver_pipeline"]
    print(f"pipeline_config = {pipeline_config}")
    pipeline = SolverPipelineABC.from_config(pipeline_config)

    query = "余额宝存入一万元，123天可以挣多少钱"
    result = asyncio.run(qa(pipeline, query))
    print(result)

    # query = "余额宝存入一万元，考虑复利的情况下，123天可以挣多少钱"
    # result = asyncio.run(qa(pipeline, query))
    # print(result)
