import re
from typing import List

from kag.interface import Task, PlannerABC


@PlannerABC.register("mcp_planner")
class MCPPlanner(PlannerABC):
    """mcp planner that generates task plans"""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    async def ainvoke(self, query, **kwargs) -> List[Task]:
        """Asynchronously generates task plan without LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        task = Task("mcp", arguments={"query": query})
        return [task]

    def check_require_rewrite(self, task: Task):
        return False
