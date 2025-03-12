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
from tenacity import stop_after_attempt, retry
from kag.interface import (
    SolverPipelineABC,
    PlannerABC,
    ExecutorABC,
    GeneratorABC,
    Context,
)


@SolverPipelineABC.register("kag_iterative_pipeline")
class KAGIterativePipeline(SolverPipelineABC):
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
        # append a finish executor to indicate task is finished.
        self.finish_executor = ExecutorABC.from_config({"type": "finish_executor"})
        self.executors.append(self.finish_executor)

    def select_executor(self, executor_name: str):
        for executor in self.executors:
            schema = executor.schema()
            if executor_name == schema["name"]:
                return executor
        return None

    #@retry(stop=stop_after_attempt(3))
    async def planning(self, query, context, **kwargs):
        task = await self.planner.ainvoke(
            query,
            context=context,
            executors=[x.schema() for x in self.executors],
            **kwargs,
        )
        if isinstance(task, list):
            task = task[0]
        executor = self.select_executor(task.executor)
        if not executor:
            raise ValueError(f"Executor {task.executor} not in acceptable executors.")
        return task, executor

    async def ainvoke(self, query, **kwargs):
        num_iteration = 0
        context: Context = Context()
        success = False
        while num_iteration < self.max_iteration:
            num_iteration += 1
            task, executor = await self.planning(query, context, **kwargs)
            if executor == self.finish_executor:
                success = True
                break
            context.append_task(task)
            await executor.ainvoke(query, task, context, **kwargs)
        if success:
            answer = await self.generator.ainvoke(query, context)
            return answer
