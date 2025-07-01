import asyncio

from kag.common.registry import import_modules_from_path
from kag.open_benchmark.utils.eval_qa import EvalQa


async def qa(query):
    qa_obj = EvalQa(task_name="baike", solver_pipeline_name="kag_solver_pipeline")
    answer, trace = await qa_obj.qa(query=query, gold="")
    print(f"{query} is {answer}")


if __name__ == "__main__":
    import_modules_from_path("./prompt")
    queries = [
        "周星驰的姓名有何含义？",
        # "周星驰和万梓良有什么关系",
        # "周星驰在首部自编自导自演的电影中，票房达到多少，他在其中扮演什么角色",
        # "周杰伦曾经为哪些自己出演的电影创作主题曲？",
        # "周杰伦在春晚上演唱过什么歌曲？是在哪一年",
    ]
    for query in queries:
        asyncio.run(qa(query))
