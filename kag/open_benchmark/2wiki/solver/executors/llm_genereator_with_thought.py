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
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    to_reference_list,
)
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@GeneratorABC.register("llm_generator_with_thought")
class LLMGeneratorWithThought(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        chunk_reranker: RerankByVector = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt
        self.chunk_reranker = chunk_reranker or RerankByVector.from_config(
            {
                "type": "rerank_by_vector",
            }
        )

    def invoke(self, query, context, **kwargs):
        results = []
        rerank_queries = []
        chunks = []
        thoughts = []
        for task in context.gen_task(False):
            task_result = json.loads(task.result)
            subq = task_result["query"]
            suba = task_result["response"]
            thoughts.append(f"Sub-Query: {subq}\n{suba}")
            retrieved_docs = task.memory.get("retriever")
            if retrieved_docs and self.chunk_reranker:
                rerank_queries.append(task.arguments["query"])
                chunks.append(retrieved_docs.chunk_datas)
        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        total_reference_source = rerank_chunks
        refer_data = to_reference_list(
            prefix_id=0, retrieved_datas=total_reference_source
        )

        refer_data = [
            f"Wikipedia Title:{x['document_name']}\n{x['content']}" for x in refer_data
        ]
        refer_data = "\n\n".join(refer_data)
        thoughts = "\n\n".join(thoughts)
        #         system_instruction = """
        # As an advanced reading comprehension assistant, your task is to analyze text passages and corresponding questions meticulously. Your response start after "Thought: ", where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.NOTE: \n1. I hope your answer matches the answer exactly, so ENSURE that the answer following "Answer:" is concise, such as 14 May, 1832  or yes. THE SHORTER, THE BETTER!! 2. If the answer is a date, please provide the full date as much as possible, such as 18 May, 1932.3. Pay attention to the differences in part of speech, such as "Japan" and "Japanese," and provide the accurate format according to the question. If you believe the provided documents cannot answer the question, response with Answer: UNKNOWN.

        # Wikipedia Title: Kurram Garhi
        # Kurram Garhi is a small village located near the city of Bannu, which is the part of Khyber Pakhtunkhwa province of Pakistan. Its population is approximately 35000. Barren hills are near this village. This village is on the border of Kurram Agency. Other nearby villages are Peppal, Surwangi and Amandi Kala.

        # Wikipedia Title: 2001–02 UEFA Champions League second group stage
        # Eight winners and eight runners- up from the first group stage were drawn into four groups of four teams, each containing two group winners and two runners- up. Teams from the same country or from the same first round group could not be drawn together. The top two teams in each group advanced to the quarter- finals.

        # Wikipedia Title: Satellite tournament
        # A satellite tournament is either a minor tournament or event on a competitive sporting tour or one of a group of such tournaments that form a series played in the same country or region.

        # Wikipedia Title: Trojkrsti
        # Trojkrsti is a village in Municipality of Prilep, Republic of Macedonia.

        # Wikipedia Title: Telephone numbers in Ascension Island
        # Country Code:+ 247< br> International Call Prefix: 00 Ascension Island does not share the same country code( +290) with the rest of St Helena.

        # Q: Are both Kurram Garhi and Trojkrsti located in the same country?
        # Thought: Kurram Garhi is located in the country of Pakistan. Trojkrsti is located in the country of Republic of Macedonia. Thus, they are not in the same country.  Answer: no.
        #         """

        system_instruction = """
As an advanced reading comprehension assistant, your task is to answer complex multi-hop questions based on the context I provide. The context I offer includes two parts: a set of documents that are helpful for answering the question, and a step-by-step breakdown of the question along with an analytical thought process. Please combine these two parts of the context to answer the question. Your response start after "Thought: ", where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.NOTE: \n1. I hope your answer matches the answer exactly, so ENSURE that the answer following "Answer:" is concise, such as 14 May, 1832  or yes. THE SHORTER, THE BETTER!! 2. If the answer is a date, please provide the full date as much as possible, such as 18 May, 1932.3. Pay attention to the differences in part of speech, such as "Japan" and "Japanese," and provide the accurate format according to the question. If you believe the provided documents cannot answer the question, response with Answer: UNKNOWN.
"""

        prompt = f"{system_instruction}\n\nDocs:\n{refer_data}\nStep by Step Analysis:\n{thoughts}Question: {query}"
        # print(f"llm generator prompt = {prompt}")
        response = self.llm_client(prompt)
        if "Answer: " not in response:
            raise ValueError(f"no answer found in response: {response}")
        # print(f"llm generator response = {response}")
        answer = response.split("Answer:")[1].strip()
        # if "UNKNOWN" in answer:
        #     from kag.common.utils import red, reset

        #     print(
        #         f"{red}INCORRECT==========================\n{prompt}==========\n{response}=========={reset}"
        #     )
        return answer

    def invoke(self, query, context, **kwargs):
        results = []
        rerank_queries = []
        chunks = []
        thoughts = []
        for task in context.gen_task(False):
            task_result = json.loads(task.result)
            subq = task_result["query"]
            suba = task_result["response"]
            thoughts.append(f"SubQuestion: {subq}\n{suba}")
            retrieved_docs = task.memory.get("retriever")
            if retrieved_docs and self.chunk_reranker:
                rerank_queries.append(task.arguments["query"])
                chunks.append(retrieved_docs.chunk_datas)
        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        total_reference_source = rerank_chunks
        refer_data = to_reference_list(
            prefix_id=0, retrieved_datas=total_reference_source
        )
        refer_data = [x["content"] for x in refer_data]

        results = {"reference": refer_data, "step by step analysis": thoughts}
        return self.llm_client.invoke(
            {"query": query, "content": results},
            self.generated_prompt,
            segment_name="answer",
            tag_name="Final Answer",
            **kwargs,
        )
