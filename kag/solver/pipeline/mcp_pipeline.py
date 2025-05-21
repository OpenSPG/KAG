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
)

logger = logging.getLogger(__name__)


@SolverPipelineABC.register("mcp_pipeline")
class MCPPipeline(SolverPipelineABC):
    def __init__(
        self,
        planner: PlannerABC,
        executors: List[ExecutorABC],
        generator: GeneratorABC,
        max_iteration: int = 5,
    ):
        super().__init__()
        self.planner = planner
        self.executors = executors
        self.generator = generator
        self.max_iteration = max_iteration

    def select_mcp_server(self, mcp_server_name: str):
        """Select executor instance by name from available executors.
        Args:
            mcp_server_name: The server name to retrieve
        Returns:
            Matching executor instance, or None if not found
        """
        mcp_schema_data = self.executor.schema()

        for server in mcp_schema_data.get("available_servers", []):
            if server["name"] == mcp_server_name:
                return {"name": server["name"], "desc": server["desc"]}
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
        tasks = await self.planner.ainvoke(
            query,
            context=context,
            executors=[x.schema() for x in self.executors],
            **kwargs,
        )
        return tasks

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def execute_task(self, query, task, context, **kwargs):
        """Executes single task with query rewriting and executor invocation.

        Args:
            query: Original user query
            task: Task instance to execute
            context: Execution context for dependency resolution
            **kwargs: Additional execution parameters
        """
        if self.planner.check_require_rewrite(task):
            task.update_memory("origin_arguments", task.arguments)
            task.arguments = await self.planner.query_rewrite(task, **kwargs)
        mcp_server = self.select_mcp_server(task.executor)
        if mcp_server:
            await self.executors[0].ainvoke(query, task, context, **kwargs)
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
