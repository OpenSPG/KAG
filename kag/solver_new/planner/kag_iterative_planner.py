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

from typing import List

from kag.interface import PlannerABC, Task, LLMClient, PromptABC, Context


@PlannerABC.register("kag_iterative_planner")
class KAGIterativePlanner(PlannerABC):
    def __init__(self, executors, llm: LLMClient, plan_prompt: PromptABC):
        super().__init__(executors)
        self.llm = llm
        self.plan_prompt = plan_prompt

    def format_context(self, context: Context = None):
        formatted_context = []
        # get all prvious tasks from context.
        if context and isinstance(context, Context):
            task_dag = context.get_dag()
            for task in task_dag:
                formatted_context.append(
                    {
                        "action": {"name": task.executor, "argument": task.arguments},
                        "result": task.result,
                    }
                )
        return formatted_context

    def invoke(self, query, **kwargs) -> List[Task]:
        return self.llm.invoke(
            {
                "query": query,
                "context": self.format_context(kwargs.get("context")),
                "executors": [executor.schema() for executor in self.executors],
            },
            self.plan_prompt,
        )

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        return await self.llm.ainvoke(
            {
                "query": query,
                "context": self.format_context(kwargs.get("context")),
                "executors": [executor.schema() for executor in self.executors],
            },
            self.plan_prompt,
        )

    def decompose_task(self, task: Task, **kwargs) -> List[Task]:
        raise NotImplementedError("decompose_task not implemented yet.")

    def compose_task(self, task: Task, children_tasks: List[Task], **kwargs):
        raise NotImplementedError("compose_task not implemented yet.")
