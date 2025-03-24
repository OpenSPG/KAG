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
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_hybrid_executor import \
    KAGRetrievedResponse, to_reference_list
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@GeneratorABC.register("llm_generator")
class LLMGenerator(GeneratorABC):
    def __init__(self, llm_client: LLMClient, generated_prompt: PromptABC, chunk_reranker:RerankByVector=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt
        self.chunk_reranker = chunk_reranker or RerankByVector.from_config({
            "type": "rerank_by_vector",
        })

    def invoke(self, query, context, **kwargs):
        results = []
        rerank_queries = []
        chunks = []
        graph_data = []
        for task in context.gen_task(False):
            if isinstance(task.result, KAGRetrievedResponse) and self.chunk_reranker:
                rerank_queries.append(task.arguments['query'])
                graph_data.append(task.result.graph_data)
                chunks.append(task.result.chunk_datas)
            else:
                results.append(
                    str(task.result)
                )
        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        total_reference_source = graph_data + rerank_chunks
        refer_data = to_reference_list(prefix_id=0, retrieved_datas=total_reference_source)
        if rerank_chunks:
            results.append({
                "reference": refer_data
            })
        return self.llm_client.invoke({
            "query": query,
            "content": results
        }, self.generated_prompt, segment_name="answer", tag_name="Final Answer", **kwargs)