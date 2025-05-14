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
import asyncio
from typing import List
from kag.interface import (
    ExecutorABC,
    RetrieverABC,
    RetrieverOutputMerger,
    RetrieverOutput,
    Task,
    Context,
)


@ExecutorABC.register("kag_hybrid_retrieval_executor")
class KAGHybridRetrievalExecutor(ExecutorABC):
    def __init__(
        self,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
    ):
        self.retrievers = retrievers
        self.merger = merger

    def inovke(
        self, query: str, task: Task, context: Context, **kwargs
    ) -> RetrieverOutput:
        task_query = task.arguments["query"]
        outputs = []
        for retriever in self.retrievers:
            outputs.append(retriever.invoke(task_query, **kwargs))

        merged = self.merger.invoke(task_query, outputs, **kwargs)
        return merged

    async def ainvoke(
        self, query: str, task: Task, context: Context, **kwargs
    ) -> RetrieverOutput:
        task_query = task.arguments["query"]
        print(f"task_query = {task_query}")
        tasks = []
        for retriever in self.retrievers:
            tasks.append(asyncio.create_task(retriever.ainvoke(task_query, **kwargs)))
        outputs = await asyncio.gather(*tasks)
        merged = await self.merger.ainvoke(task_query, outputs, **kwargs)
        return merged

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "Retriever",
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
