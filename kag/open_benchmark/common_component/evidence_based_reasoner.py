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
from typing import List
from kag.interface import (
    ExecutorABC,
    LLMClient,
    Task,
    Context,
    RetrieverOutputMerger,
    RetrieverABC,
)


@ExecutorABC.register("evidence_based_reasoner")
class EvidenceBasedReasoner(ExecutorABC):
    def __init__(
        self,
        llm: LLMClient,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
    ):
        self.llm = llm
        self.retrievers = retrievers
        self.merger = merger

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):

        retrieval_futures = []
        for retriever in self.retrievers:
            retrieval_futures.append(
                asyncio.create_task(retriever.ainvoke(task, **kwargs))
            )
        outputs = await asyncio.gather(*retrieval_futures)
        merged = await self.merger.ainvoke(task, outputs, **kwargs)

        retrieved_docs = []
        for chunk in merged.chunks:
            retrieved_docs.append(chunk.content)
        retrieved_docs = "\n\n".join(retrieved_docs)

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
        request = f"{system_instruction}\nDocs:\n{retrieved_docs}\nQuestions:\n{subqa}\n{query}"

        # print(f"Reasoner request = {request}")
        response = await self.llm.acall(request)
        # print(f"Reasoner response = {response}")
        task.update_memory("retriever", merged)
        task.result = json.dumps(
            {"query": task.arguments["query"], "response": response}, ensure_ascii=False
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
