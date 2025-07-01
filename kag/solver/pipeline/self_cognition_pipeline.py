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
import logging
from typing import List
from tenacity import stop_after_attempt, retry
from kag.interface import (
    SolverPipelineABC,
    ExecutorABC,
    GeneratorABC,
    Context,
    Task,
)
from kag.common.tools.algorithm_tool.self_cognition.self_cogn_tools import (
    SelfCognExecutor,
)

logger = logging.getLogger(__name__)


@SolverPipelineABC.register("self_cognition_pipeline")
class SelfCognitionPipeline(SolverPipelineABC):
    """Pipeline self cognition pipeline.
    Args:
        executors (List[ExecutorABC]): Available executor instances for task execution
        generator (GeneratorABC): Result generation component for final answer synthesis
    """

    def __init__(
        self,
        self_cogn_tool: SelfCognExecutor,
        generator: GeneratorABC,
    ):
        super().__init__()
        self.self_cogn_tool = self_cogn_tool
        self.generator = generator

    @retry(stop=stop_after_attempt(3))
    async def planning(self, query, context, **kwargs):
        """Generates task plan through LLM-based planning with automatic retry.

        Args:
            query: Original user query
            context: Execution context containing previous task results
            **kwargs: Additional planning parameters

        Returns:
            List[Task]: Planned task sequence in DAG format
        """
        tasks_dep = {}
        tasks_dep[0] = {
            "executor": "SelfCognition",
            "dependent_task_ids": [],
            "arguments": {"query": query},
        }
        return Task.create_tasks_from_dag(tasks_dep)

    async def execute_task(self, query, task, context, **kwargs):
        """Executes single task with query rewriting and executor invocation.

        Args:
            query: Original user query
            task: Task instance to execute
            context: Execution context for dependency resolution
            **kwargs: Additional execution parameters
        """
        task.update_result(self.self_cogn_tool.get_docs())

    async def ainvoke(self, query, **kwargs):
        is_self_cognition_query = self.self_cogn_tool.invoke(query, **kwargs)
        if not is_self_cognition_query:
            return None
        context: Context = Context()
        tasks = await self.planning(query, context, **kwargs)

        for task in tasks:
            context.add_task(task)

        for task_group in context.gen_task(group=True):
            await asyncio.gather(
                *[
                    asyncio.create_task(
                        self.execute_task(query, task, context, **kwargs)
                    )
                    for task in task_group
                ]
            )

        answer = await self.generator.ainvoke(query, context, **kwargs)
        from kag.common.utils import red, green, reset

        task_info = []
        for task in context.gen_task(group=False):
            task_info.append(
                {
                    "task": task.arguments,
                    "memory": task.memory,
                    "result": task.result,
                }
            )
        if answer is None:
            print(f"{red}Failed to answer quesion: {query}\nTasks:{task_info}\n{reset}")
            return "UNKNOWN"
        print(
            f"{green}Input Query: {query}\n\nTasks:\n\n{task_info}\n\nFinal Answer: {answer}"
        )
        return answer
