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
from kag.interface import (
    SolverPipelineABC,
    GeneratorABC,
    Context,
)

logger = logging.getLogger(__name__)


@SolverPipelineABC.register("naive_generation_pipeline")
class NaiveGenerationPipeline(SolverPipelineABC):
    """
    Pipeline using LLM to directly generate answers.
    Args:
        generator (GeneratorABC): Result generation component for final answer synthesis
        max_iteration (int): Maximum allowed execution iterations (default: 10)
    """

    def __init__(
        self,
        generator: GeneratorABC,
    ):
        super().__init__()
        self.generator = generator

    async def ainvoke(self, query, **kwargs):
        """Orchestrates full problem-solving workflow asynchronously.

        Execution flow:
        1. Generate initial task DAG
        2. Execute tasks in parallel batches
        3. Generate final answer from execution context

        Args:
            query: User query to solve
            **kwargs: Additional execution parameters

        Returns:
            Final generated answer from the execution context
        """
        context: Context = Context()
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
            f"{green}Input Query: {query}\n\nTasks:\n\n{task_info}\n\nFinal Answer: {answer}\nGold Answer: {kwargs.get('gold')}{reset}"
        )
        return answer
