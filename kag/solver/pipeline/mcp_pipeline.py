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
            max_iteration: int = 10,
    ):
        super().__init__()
        self.planner = planner
        self.executors = executors
        self.generator = generator
        self.max_iteration = max_iteration

    def select_mcp_server_executor(self, executor_name: str):
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
            context=context
        )
        return tasks