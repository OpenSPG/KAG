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
import json
import re
from typing import List, Optional

from kag.interface import PlannerABC, Task, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC


@PlannerABC.register("lf_kag_static_planner")
class KAGLFStaticPlanner(PlannerABC):
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

    def format_context(self, tasks: List[Task]):
        """Formats parent task execution context into a structured dictionary.

        Args:
            task (Task): Current task whose parent context needs formatting

        Returns:
            dict: Mapping of parent task IDs to their execution details containing:
                - action: Executor and arguments used
                - result: Execution result of the parent task
        """
        def to_str(context):
            return f"""{context['name']}:{context['task']}
answer: {context['result']}.{context.get('thought', '')}"""
        if not tasks:
            return []
        formatted_context = []
        if isinstance(tasks, Task):
            tasks = [tasks]
        for task in tasks:
            # get all prvious tasks from context.
            formatted_context.extend(self.format_context(task.parents))
            formatted_context.append(to_str(task.get_task_context(with_all=True)))
        return formatted_context

    def check_require_rewrite(self, task: Task):
        """Determines if query rewriting is needed based on parameter patterns.

        Args:
            task (Task): Task to check for rewrite requirements

        Returns:
            bool: True if query contains dynamic parameter references (e.g., {{1.output}})
        """
        return task.arguments.get('is_need_rewrite', False)

    async def query_rewrite(self, task: Task, **kwargs):
        """Performs asynchronous query rewriting using LLM and context.

        Args:
            task (Task): Task containing the query to rewrite

        Returns:
            str: Rewritten query with resolved dynamic references
        """
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)

        query = task.arguments['query']
        tag_id = f"{query}_begin_task"

        if reporter:
            reporter.add_report_line(segment="thinker", tag_name=tag_id, content="", status="INIT", step=task.name, overwrite=False)
        # print(f"Old query: {query}")
        deps_context = self.format_context(task.parents)
        context = {
            "target question": kwargs.get("query"),
            "history_qa": deps_context,
        }
        new_query = await self.llm.ainvoke(
            {
                "input": query,
                "content": json.dumps(context, indent=2, ensure_ascii=False),
            },
            self.rewrite_prompt,
            segment_name=tag_id,
            tag_name="Rewrite query",
            with_json_parse=self.rewrite_prompt.is_json_format(),
            **kwargs,
        )
        logic_form_node = task.arguments.get("logic_form_node", None)
        if logic_form_node:
            logic_form_node.sub_query = new_query
            return {
                "logic_form_node": logic_form_node
            }
        # print(f"query rewrite context = {context}")
        # print(f"New query: {new_query}")
        return {
            "query": new_query
        }

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
        retry_num = 3
        while retry_num > 0:
            try:
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
            except Exception as e:
                retry_num -= 1
                if retry_num == 0:
                    raise e


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
