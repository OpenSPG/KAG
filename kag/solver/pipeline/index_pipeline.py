import asyncio
import logging
from typing import List
from tenacity import stop_after_attempt, retry
from kag.interface import (
    SolverPipelineABC,
    PlannerABC,
    ExecutorABC,
    GeneratorABC,
    Context,
    Task,
)

logger = logging.getLogger(__name__)


@SolverPipelineABC.register("index_pipeline")
class IndexPipeline(SolverPipelineABC):
    def __init__(
        self,
        executors: List[ExecutorABC],
        generator: GeneratorABC,
        max_iteration: int = 5,
    ):
        super().__init__()
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

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def planning(self, query, context, **kwargs):
        """Generates task plan through LLM-based planning with automatic retry.

        Args:
            query: Original user query
            context: Execution context containing previous task results
            **kwargs: Additional planning parameters

        Returns:
            List[Task]: Planned task sequence in DAG format
        """

        return [Task(executor="Retriever", arguments={"query": query})]

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def execute_task(self, query, task, context, **kwargs):
        """Executes single task with query rewriting and executor invocation.

        Args:
            query: Original user query
            task: Task instance to execute
            context: Execution context for dependency resolution
            **kwargs: Additional execution parameters
        """
        executor = self.select_executor(task.executor)
        if executor:
            await executor.ainvoke(query, task, context, **kwargs)
        else:
            logger.warn(f"Executor not  found for task {task}")

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

        return answer
