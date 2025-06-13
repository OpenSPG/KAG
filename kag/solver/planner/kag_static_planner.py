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
import logging
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
        self,
        llm: LLMClient,
        plan_prompt: PromptABC,
        rewrite_prompt: PromptABC,
        **kwargs,
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
                "query": parent_task.arguments["query"],
                "output": str(parent_task.result),
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

    async def finish_judger(self, query: str, answer: str):
        finish_prompt = f"""
        # Task
        The answer is a response to a question. Please determine whether the content of this answer is invalid, such as  "UNKNOWN", "I don't know" or "Insufficient Information."  \n
        If the answer is invalid, return "Yes", otherwise, return "No".\n
        You output should only be "Yes" or "No".\n
        
        # Answer\n
        {answer}
        """
        try:
            response = await self.llm.acall(prompt=finish_prompt)
            if response.strip().lower() == "yes":
                return False
            return True
        except Exception as e:
            # import logging # Make sure logging is imported if not already at the top of the file
            logger = logging.getLogger(__name__)  # Get a logger instance
            logger.warning(
                f"LLM call failed in finish_judger for query '{query}'. Error: {e}",
                exc_info=True,
            )
            return False  # Treat as potentially bad answer

    async def query_rewrite(self, task: Task, **kwargs):
        """Performs asynchronous query rewriting using LLM and context.

        Args:
            task (Task): Task containing the query to rewrite

        Returns:
            str: Rewritten query with resolved dynamic references
        """
        query = task.arguments
        # print(f"Old query: {query}")
        context = self.format_context(task)
        new_query = await self.llm.ainvoke(
            {
                "input": query,
                "context": context,
            },
            self.rewrite_prompt,
            segment_name="thinker",
            tag_name="Rewrite query",
            with_json_parse=self.rewrite_prompt.is_json_format(),
            **kwargs,
        )
        # print(f"query rewrite context = {context}")
        # print(f"New query: {new_query}")
        return new_query

    def invoke(self, query, **kwargs) -> List[Task]:
        """Synchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        num_iteration = kwargs.get("num_iteration", 0)

        return self.llm.invoke(
            {
                "query": query,
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
            with_json_parse=self.plan_prompt.is_json_format(),
            segment_name="thinker",
            tag_name=f"Static planning {num_iteration}",
            **kwargs,
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
        num_iteration = kwargs.get("num_iteration", 0)
        return await self.llm.ainvoke(
            {
                "query": query,
                "executors": kwargs.get("executors", []),
            },
            self.plan_prompt,
            with_json_parse=self.plan_prompt.is_json_format(),
            segment_name="thinker",
            tag_name=f"Static planning {num_iteration}",
            **kwargs,
        )
