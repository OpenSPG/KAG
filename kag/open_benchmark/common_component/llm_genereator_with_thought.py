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
from typing import Optional

from kag.interface import GeneratorABC, LLMClient, PromptABC, RetrieverOutput
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    to_reference_list,
)
from kag.common.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


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
            task_query = task.arguments.get("rewrite_query", task.arguments["query"])
            print(f"task.result = {task.result}")
            if isinstance(task.result, RetrieverOutput):
                thoughts.append(
                    f"Sub-Query: {task.arguments['query']}\n {task.result.summary}"
                )
                retrieved_docs = task.result
            elif task.executor != "Output":
                result = str(task.result)
                try:
                    task_result = json.loads(result)
                    subq = task_result["query"]
                    suba = task_result["response"]
                    thoughts.append(f"Sub-Query: {subq}\n{suba}")
                except Exception:
                    thoughts.append(f"Sub-Query: {task_query}\n {task.result}")

                retrieved_docs = task.memory.get("retriever")
            else:
                retrieved_docs = []

            if retrieved_docs and self.chunk_reranker:
                rerank_queries.append(task_query)
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
As an advanced reading comprehension assistant, your task is to answer complex multi-hop questions based on the context I provide. The context I offer includes two parts: a set of documents that are helpful for answering the question, and a step-by-step breakdown of the question along with an analytical thought process. Please combine these two parts of the context to answer the question. Your response start after "Thought: ", where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.\n
NOTE:
1. I hope your answer matches the answer exactly, so ENSURE that the answer following "Answer:" is concise, such as 14 May, 1832  or yes. THE SHORTER, THE BETTER!!
2. If the answer is a date, please provide the full date as much as possible, such as 18 May, 1932.3. Pay attention to the differences in part of speech, such as "Japan" and "Japanese," and provide the accurate format according to the question.
3. If you believe the provided documents cannot answer the question, response with Answer: UNKNOWN.
"""

        prompt = f"{system_instruction}\n\nDocs:\n{refer_data}\nStep by Step Analysis:\n{thoughts}Question: {query}"
        response = self.llm_client(prompt)
        if "Answer: " not in response:
            raise ValueError(f"no answer found in response: {response}")
        answer = response.split("Answer:")[1].strip()

        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        if reporter:
            reporter.add_report_line(
                "generator", "final_generator_input", prompt, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference", "reference_chunk", rerank_chunks, "FINISH"
            )
        return answer
