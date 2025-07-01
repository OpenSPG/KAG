from kag.interface import Task, LLMClient
from kag.interface.solver.retriever_abc import RetrieverABC

if __name__ == "__main__":
    llm_config = {
        "api_key": "key",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max-latest",
        "type": "maas",
    }
    llm_client = LLMClient.from_config(llm_config)

    retriever_config = {
        "type": "atomic_query_chunk_retriever",
        "llm_client": llm_config,
        "query_rewrite_prompt": {"type": "atomic_query_rewrite_prompt"},
        "vectorize_model": {
            "type": "openai",
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": "key",
            "model": "BAAI/bge-m3",
            "vector_dimensions": 1024,
        },
    }
    retriever = RetrieverABC.from_config(retriever_config)
    task = Task(executor="", arguments={"query": "截至9月份止六个月财务业绩概要"})
    retrieverOuput = retriever.invoke(task=task)
    print(retrieverOuput)
