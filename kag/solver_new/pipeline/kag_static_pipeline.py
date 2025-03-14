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
from tenacity import stop_after_attempt, retry
from kag.interface import (
    SolverPipelineABC,
    PlannerABC,
    ExecutorABC,
    GeneratorABC,
    Context,
)


@SolverPipelineABC.register("kag_static_pipeline")
class KAGStaticPipeline(SolverPipelineABC):
    def __init__(
        self,
        planner: PlannerABC,
        executors: List[ExecutorABC],
        generator: GeneratorABC,
        max_iteration: int = 10,
    ):
        super().__init__()
        self.planner = planner
        self.executors = executors
        self.generator = generator
        self.max_iteration = max_iteration

    def select_executor(self, executor_name: str):
        """Select executor instance by name from available executors.

        Args:
            executor_name: Name of the executor to retrieve

        Returns:
            Matching executor instance, or None if not found
        """
        for executor in self.executors:
            schema = executor.schema()
            if executor_name == schema["name"]:
                return executor
        return None

    @retry(stop=stop_after_attempt(3))
    async def planning(self, query, context, **kwargs):
        tasks = await self.planner.ainvoke(
            query,
            context=context,
            executors=[x.schema() for x in self.executors],
            **kwargs,
        )
        return tasks

    @retry(stop=stop_after_attempt(3))
    async def execute_task(self, query, task, context, **kwargs):
        if self.planner.check_require_rewrite(task):
            print("rewrite required=============")
            print(f"original query: {task.arguments}")
            task.arguments = await self.planner.query_rewrite(task)
            print(f"rewrited query: {task.arguments}")
        executor = self.select_executor(task.executor)
        await executor.ainvoke(query, task, context, **kwargs)

    async def ainvoke(self, query, **kwargs):
        context: Context = Context()
        tasks = await self.planning(query, context, **kwargs)

        for task in tasks:
            context.add_task(task)

        for task_group in context.gen_task(group=True):
            await asyncio.gather(
                *[
                    asyncio.create_task(self.execute_task(query, task, context))
                    for task in task_group
                ]
            )

        answer = await self.generator.ainvoke(query, context)
        return answer
