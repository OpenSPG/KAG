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
    """Static planner that generates task plans using LLM with query rewriting capability.

    Args:
        llm (LLMClient): Language model client for plan generation
        plan_prompt (PromptABC): Prompt template for initial planning requests
        rewrite_prompt (PromptABC): Prompt template for query rewriting operations
    """

    def __init__(
        self, llm: LLMClient, plan_prompt: PromptABC, rewrite_prompt: PromptABC, **kwargs
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.plan_prompt = plan_prompt
        self.rewrite_prompt = rewrite_prompt

    def format_context(self, task: Task):
        """Formats parent task execution context into a structured dictionary.

        Args:
            task (Task): Current task whose parent context needs formatting

        Returns:
            dict: Mapping of parent task IDs to their execution details containing:
                - action: Executor and arguments used
                - result: Execution result of the parent task
        """
        formatted_context = {}
        # get all prvious tasks from context.
        for parent_task in task.parents:
            formatted_context[parent_task.id] = {
                "result": str(parent_task.result),
            }
        return formatted_context

    def check_require_rewrite(self, task: Task):
        """Determines if query rewriting is needed based on parameter patterns.

        Args:
            task (Task): Task to check for rewrite requirements

        Returns:
            bool: True if query contains dynamic parameter references (e.g., {{1.output}})
        """
        query = task.arguments
        pattern = r"\{\{\d+\.output\}\}"
        return bool(re.search(pattern, str(query)))

    async def query_rewrite(self, task: Task, **kwargs):
        """Performs asynchronous query rewriting using LLM and context.

        Args:
            task (Task): Task containing the query to rewrite

        Returns:
            str: Rewritten query with resolved dynamic references
        """
        query = task.arguments
        context = self.format_context(task)
        return await self.llm.ainvoke({
            "input": query,
            "context": context,
        }, self.rewrite_prompt, segment_name="thinker", tag_name="Rewrite query", **kwargs)

    def invoke(self, query, **kwargs) -> List[Task]:
        """Synchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        return self.llm.invoke(
            {
                "query": query,
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
        )

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        """Asynchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        return await self.llm.ainvoke({
            "query": query,
            "executors": kwargs.get("executors", []),
        }, self.plan_prompt, segment_name="thinker", tag_name="Static planning", **kwargs)
