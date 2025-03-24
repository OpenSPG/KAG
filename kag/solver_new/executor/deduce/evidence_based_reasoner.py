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
from kag.interface import ExecutorABC, LLMClient, Task, Context


@ExecutorABC.register("evidence_based_reasoner")
class EvidenceBasedReasoner(ExecutorABC):
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        prompt = (
            "As an advanced reading comprehension assistant, your task is to analyze text passages and corresponding questions meticulously. "
            'Your response start after "Thought: ", where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. '
            'Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.'
        )

        query = task.arguments["query"]
        docs = []
        for pt in task.parents:
            docs.append(str(pt.result))
        docs = "\n\n".join(docs)
        request = f"{prompt}\nQuery:\n{query}\nPassages:\n{docs}"
        response = await self.llm.acall(request)
        # from kag.common.utils import red, reset

        # print(f"{red}Answer To Query {query}: \nReq: {request}\nRsp: {response}{reset}")
        if "Answer:" in response:
            answer = response.split("Answer:")[1]
        else:
            answer = response
        task.result = answer

        return response

    def schema(self, func_name: str = None):
        return {
            "name": "Reasoner",
            "description": "Synthesizes precise, evidence-backed answers to user queries by analyzing provided contextual documents. Note: Contextual documents are pre-loaded and processed implicitly; no explicit context parameter is required.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query.",
                    "optional": False,
                },
            },
        }
