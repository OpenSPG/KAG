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
import re
from typing import List

from kag.interface import PlannerABC, Task, LLMClient, PromptABC


@PlannerABC.register("kag_static_planner")
class KAGStaticPlanner(PlannerABC):
    def __init__(
        self, llm: LLMClient, plan_prompt: PromptABC, rewrite_prompt: PromptABC
    ):
        super().__init__()
        self.llm = llm
        self.plan_prompt = plan_prompt
        self.rewrite_prompt = rewrite_prompt

    def format_context(self, task: Task):
        formatted_context = {}
        # get all prvious tasks from context.
        for parent_task in task.parents:
            formatted_context[parent_task.id] = {
                "action": f"{parent_task.executor}({parent_task.arguments})",
                "result": parent_task.result,
            }
        return formatted_context

    def check_require_rewrite(self, task: Task):
        query = task.arguments
        pattern = r"\{\{\d+\.output\}\}"
        return bool(re.search(pattern, str(query)))

    async def query_rewrite(self, task: Task):
        query = task.arguments
        context = self.format_context(task)
        return await self.llm.ainvoke(
            {
                "input": query,
                "context": context,
            },
            self.rewrite_prompt,
        )

    def invoke(self, query, **kwargs) -> List[Task]:
        return self.llm.invoke(
            {
                "query": query,
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
        )

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        return await self.llm.ainvoke(
            {
                "query": query,
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
        )

    def decompose_task(self, task: Task, **kwargs) -> List[Task]:
        raise NotImplementedError("decompose_task not implemented yet.")

    def compose_task(self, task: Task, children_tasks: List[Task], **kwargs):
        raise NotImplementedError("compose_task not implemented yet.")
