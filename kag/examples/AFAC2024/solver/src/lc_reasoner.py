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
import asyncio
import json
from typing import List, Optional
from kag.interface import (
    ExecutorABC,
    LLMClient,
    Task,
    Context,
    VectorizeModelABC,
    PromptABC,
    RetrieverABC,
    RetrieverOutputMerger,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from kag.interface.solver.reporter_abc import ReporterABC


@ExecutorABC.register("long_context_reasoner")
class LongContextBasedReasoner(ExecutorABC):
    def __init__(
        self,
        llm: LLMClient,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
        vectorize_model: VectorizeModelABC,
        context_select_prompt: PromptABC,
        context_select_llm: LLMClient,
    ):
        self.llm = llm
        self.retrievers = retrievers
        self.merger = merger
        self.vectorize_model = vectorize_model

        self.context_select_prompt = context_select_prompt
        self.context_select_llm = context_select_llm

    def rrf_merge(self, ppr_chunks: List, dpr_chunks: List):
        merged = {}
        for idx, chunk in enumerate(ppr_chunks):
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk["id"]][0]
                score += 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        for idx, chunk in enumerate(dpr_chunks):
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        sorted_chunks = sorted(merged.values(), key=lambda x: -x[0])
        return sorted_chunks

    def weightd_merge(self, ppr_chunks: List, dpr_chunks: List, alpha: float = 0.5):
        def min_max_normalize(chunks):
            if len(chunks) == 0:
                return []
            scores = []
            for chunk in chunks:
                score = chunk["score"]
                scores.append(score)
            max_score = max(scores)
            min_score = min(scores)
            for chunk in chunks:
                score = chunk["score"]
                score = (score - min_score) / (max_score - min_score)
                chunk["score"] = score

        min_max_normalize(ppr_chunks)
        min_max_normalize(dpr_chunks)

        ppr_scores = [x["score"] for x in ppr_chunks]
        dpr_scores = [x["score"] for x in dpr_chunks]
        merged = {}
        for chunk in ppr_chunks:
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += chunk["score"] * alpha
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = chunk["score"] * alpha
                merged[chunk_attr["id"]] = (score, chunk_attr)

        for chunk in dpr_chunks:
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += chunk["score"] * (1 - alpha)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = chunk["score"] * (1 - alpha)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        sorted_chunks = sorted(merged.values(), key=lambda x: -x[0])
        return sorted_chunks

    async def batch_retrieve(self, task: Task, **kwargs):
        retrieval_futures = []
        for retriever in self.retrievers:
            retrieval_futures.append(
                asyncio.create_task(retriever.ainvoke(task, **kwargs))
            )
        outputs = await asyncio.gather(*retrieval_futures)
        merged = await self.merger.ainvoke(task, outputs, **kwargs)

        return merged

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def context_select(self, query: str, sorted_chunks):
        chunks = []
        for idx, item in enumerate(sorted_chunks):
            chunks.append({"idx": idx, "content": item.content})
        variables = {"question": query, "context": chunks}
        response = await self.context_select_llm.ainvoke(
            variables, self.context_select_prompt
        )
        selected_context = response["context"]
        answer = response["answer"]
        indices = []
        if len(selected_context) > 0:
            indices.extend(selected_context)
        for i in range(min(4, len(sorted_chunks))):
            if i not in indices:
                indices.append(i)
        return [sorted_chunks[x] for x in indices]

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]
        retrieve_output = await self.batch_retrieve(task, **kwargs)
        try:
            selected_chunks = await self.context_select(
                task_query, retrieve_output.chunks
            )
        except Exception as e:
            import traceback

            traceback.print_exc()

        formatted_docs = []
        for chunk in selected_chunks:
            formatted_docs.append(f"{chunk.content}")

        formatted_docs = "\n\n".join(formatted_docs)
        system_instruction = """
As an adept specialist in resolving intricate multi-hop questions, I require your assistance in addressing a multi-hop question. The question has been segmented into multiple straightforward single-hop inquiries, wherein each question may depend on the responses to preceding questions, i.e., the question body may contain content such as "{{i.output}}", which means the answer of ith sub-question. I will furnish you with insights on how to address these preliminary questions, or the answers themselves, which are essential for accurate resolution. Furthermore, I will provide textual excerpts pertinent to the current question, which you are advised to peruse and comprehend thoroughly. Begin your reply with "Thought: ", where you'll outline the step-by-step thought process that leads to your conclusion. End with "Answer: " to deliver a clear and precise response without any extra commentary.
        
Docs:
Sylvester
Sylvester is a name derived from the Latin adjective silvestris meaning ``wooded ''or`` wild'', which derives from the noun silva meaning ``woodland ''. Classical Latin spells this with i. In Classical Latin y represented a separate sound distinct from i, not a native Latin sound but one used in transcriptions of foreign words. After the Classical period y came to be pronounced as i. Spellings with Sylv - in place of Silv - date from after the Classical period.

Stanton Township, Champaign County, Illinois
Stanton Township is a township in Champaign County, Illinois, USA. As of the 2010 census, its population was 505 and it contained 202 housing units.


Montebello, New York
Montebello (Italian: "Beautiful mountain") is an incorporated village in the town of Ramapo, Rockland County, New York, United States. It is located north of Suffern, east of Hillburn, south of Wesley Hills, and west of Airmont. The population was 4,526 at the 2010 census

Erik Hort
Erik Hort (born February 16, 1987 in Montebello, New York) is an American soccer player who is currently a Free Agent.


Questions:
0: Who was crowned emperor of the west in 800 CE?
Thought: One of the provided passage on Charlemagne indicates that he was crowned Holy Roman Emperor in 800. Answer: Charlemagne.

1: What was {{0.output}} later known as?
Thought: To determine what {{0.oputput}} (Charlemagne) was later known as, I need to review the provided passage about Charlemagne. The passage indicates that Charlemagne was also known as "Charles the Great." Answer: Charles the Great

2: What was the language from which the last name Sylvester originated during {{0.output}} era?
Thought: The question asks about the origin of the last name Sylvester during the time of the person {{0.output}}, which was Charlemagne, whose reign was in the Early Middle Ages. The passage about the name Sylvester states that it is derived from Latin. Answer: Latin
"""
        query = f"{task.id}: {task.arguments['query']}"
        subqa = []
        for pt in task.parents:
            subq = f"{pt.id}: {pt.arguments['query']}"
            result = json.loads(pt.result)
            suba = str(result["response"])
            subqa.append(f"{subq}\n{suba}")
        subqa = "\n\n".join(subqa)
        request = f"{system_instruction}\nDocs:\n{formatted_docs}\nQuestions:\n{subqa}\n{query}"

        response = await self.llm.acall(request)
        task.update_memory("retriever", retrieve_output)
        task.result = json.dumps(
            {"query": task.arguments["query"], "response": response}, ensure_ascii=False
        )

        reporter.add_report_line(
            "reference",
            f"{query}_kag_retriever_result",
            retrieve_output,
            "FINISH",
        )

        return response

    def schema(self, func_name: str = None):
        return {
            "name": "Retriever",
            "description": "Synthesizes precise, evidence-backed answers to user queries by analyzing provided contextual documents. Note: Contextual documents are pre-loaded and processed implicitly; no explicit context parameter is required.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query.",
                    "optional": False,
                },
            },
        }
