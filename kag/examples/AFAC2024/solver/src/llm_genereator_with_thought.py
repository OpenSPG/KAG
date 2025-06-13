# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
# flake8: noqa
import json

from kag.common.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector
from kag.interface import GeneratorABC, LLMClient
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    to_reference_list,
)


@GeneratorABC.register("llm_generator_with_thought")
class LLMGeneratorWithThought(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        chunk_reranker: RerankByVector = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.chunk_reranker = chunk_reranker or RerankByVector.from_config(
            {
                "type": "rerank_by_vector",
            }
        )

    def invoke(self, query, context, **kwargs):
        rerank_queries = []
        chunks = []
        thoughts = []
        for task in context.gen_task(False):
            print(f"task.result = {task.result}")
            if task.result is None:
                continue
            if task.executor == "Math":
                subq = task.arguments["query"]
                suba = task.result
            else:
                task_result = json.loads(task.result)
                subq = task_result["query"]
                suba = task_result["response"]
            thoughts.append(f"Sub-Query: {subq}\n{suba}")
            retrieved_docs = task.memory.get("retriever")
            if retrieved_docs and self.chunk_reranker:
                rerank_queries.append(task.arguments["query"])
                chunks.append(retrieved_docs.chunks)
        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        total_reference_source = rerank_chunks
        refer_data = to_reference_list(
            prefix_id=0, retrieved_datas=total_reference_source
        )

        refer_data = [f"Title:{x['document_name']}\n{x['content']}" for x in refer_data]
        refer_data = "\n\n".join(refer_data)
        thoughts = "\n\n".join(thoughts)

        system_instruction = """
            作为一名高级阅读理解助手，你的任务是根据我提供的上下文回答复杂的多跳问题。我提供的上下文包含两部分：一组有助于回答问题的文档，以及对问题的逐步分解和分析性思维过程。请结合这两部分上下文来回答问题。你的回答应从“思考：”之后开始，逐步系统地分解推理过程，并说明你是如何得出结论的。最后以“答案：”结尾，给出明确的答案，以及对应的理由。\n
            注意：
            1. 我希望你的答案与召回文档完全一致。
            2. 如果您认为所提供的文件无法回答问题，请回答“未知”。
            3. 未知也要回答“答案： 未知”。
            """

        prompt = f"{system_instruction}\n\n召回文档:\n{refer_data}\n思考:\n{thoughts}\n\n问题: {query}"
        response = self.llm_client(prompt)
        if "答案" not in response:
            raise ValueError(f"no answer found in response: {response}")
        answer = response.split("答案")[-1].strip().lstrip("：").lstrip(":")
        return answer
