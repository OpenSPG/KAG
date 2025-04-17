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
from kag.interface import ExecutorABC, LLMClient, Task, Context


@ExecutorABC.register("evidence_based_reasoner")
class EvidenceBasedReasoner(ExecutorABC):
    def __init__(self, llm: LLMClient, retriever: ExecutorABC):
        self.llm = llm
        self.retriever = retriever

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        retrieve_task = Task(
            executor=self.retriever.schema()["name"],
            arguments=task.arguments,
            id=task.id,
        )
        await asyncio.to_thread(
            lambda: self.retriever.invoke(query, retrieve_task, context)
        )

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
