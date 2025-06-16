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


class MaxIterationsReachedError(RuntimeError):
    pass


@SolverPipelineABC.register("kag_iterative_pipeline")
class KAGIterativePipeline(SolverPipelineABC):
    """Iterative problem-solving pipeline that decomposes and analyzes problems step-by-step.

    This pipeline coordinates planners, executors, and generators to solve problems through
    repeated planning and execution cycles until completion or iteration limit is reached.
    """

    def __init__(
        self,
        planner: PlannerABC,
        executors: List[ExecutorABC],
        generator: GeneratorABC,
        max_iteration: int = 5,
    ):
        """Initialize the iterative pipeline.

        Args:
            planner: Component responsible for generating execution plans
            executors: List of available executor components for task execution
            generator: Component that generates final answers from context
            max_iteration: Maximum number of allowed execution cycles (default: 5)
        """
        super().__init__()
        self.planner = planner
        self.executors = executors
        self.generator = generator
        self.max_iteration = max_iteration
        # append a finish executor to indicate task is finished.
        self.finish_executor = ExecutorABC.from_config({"type": "finish_executor"})
        self.executors.append(self.finish_executor)

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

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def planning(self, query, context, **kwargs):
        """Perform planning phase to determine next execution step.

        Args:
            query: Original user query being processed
            context: Current execution context containing historical tasks
            **kwargs: Additional execution parameters

        Returns:
            Tuple containing the planned task and corresponding executor

        Raises:
            ValueError: If the required executor is not available
        """
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
        """Execute the problem-solving process for given query.

        Args:
            query: User query to solve
            **kwargs: Additional execution parameters

        Returns:
            Generated answer from the final context

        Raises:
            MaxIterationsReachedError: If maximum iterations reached without completion
        """
        num_iteration = 0
        context: Context = Context()
        finished_by_executor = False  # Initialize flag
        while num_iteration < self.max_iteration:
            num_iteration += 1
            task, executor = await self.planning(
                query, context, num_iteration=num_iteration, **kwargs
            )

            if executor == self.finish_executor:
                context.append_task(task)  # Add finish task to context
                finished_by_executor = True
                break

            # Execute the task first
            await executor.ainvoke(query, task, context, **kwargs)
            # Add task to context only after successful execution
            context.append_task(task)

        if not finished_by_executor:
            raise MaxIterationsReachedError(
                f"Pipeline reached max_iteration ({self.max_iteration}) "
                f"without finishing for query: {query}"
            )

        answer = await self.generator.ainvoke(query, context, **kwargs)
        return answer
