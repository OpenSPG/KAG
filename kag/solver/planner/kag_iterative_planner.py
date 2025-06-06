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
    """Iterative planner that uses LLM to generate task plans based on context and available executors.

    Args:
        llm (LLMClient): Language model client for plan generation
        plan_prompt (PromptABC): Prompt template for planning requests
    """

    def __init__(self, llm: LLMClient, plan_prompt: PromptABC, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.plan_prompt = plan_prompt

    def format_context(self, context: Context = None):
        """Formats execution context into a structured list of previous task results.

        Args:
            context (Context, optional): Execution context containing task history

        Returns:
            list: Structured representation of previous tasks with actions and results
        """
        formatted_context = []
        # get all prvious tasks from context.
        if context and isinstance(context, Context):

            for task in context.gen_task():
                formatted_context.append(
                    {
                        "action": {"name": task.executor, "argument": task.arguments},
                        "result": (
                            task.result.to_string()
                            if hasattr(task.result, "to_string")
                            else task.result
                        ),
                    }
                )
        return formatted_context

    def invoke(self, query, **kwargs) -> List[Task]:
        """Synchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - context (Context): Execution context
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        num_iteration = kwargs.get("num_iteration", 0)
        return self.llm.invoke(
            {
                "query": query,
                "context": self.format_context(kwargs.get("context")),
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
            segment_name="thinker",
            tag_name=f"Iterative planning {num_iteration}",
            **kwargs,
        )

    def is_static(self):
        return False

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        """Asynchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - context (Context): Execution context
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        num_iteration = kwargs.get("num_iteration", 0)
        return await self.llm.ainvoke(
            {
                "query": query,
                "context": self.format_context(kwargs.get("context")),
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
            segment_name="thinker",
            tag_name=f"Iterative planning {num_iteration}",
            **kwargs,
        )
