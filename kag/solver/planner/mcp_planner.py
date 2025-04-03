import re
from typing import List

from kag.interface import PlannerABC, Task, LLMClient, PromptABC


@PlannerABC.register("mcp_planner")
class McpPlanner(PlannerABC):
    """mcp planner that generates task plans using LLM with query rewriting capability.

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
                "mcp_servers": kwargs.get("mcp_servers", []),
            },

            segment_name="thinker",
            tag_name=f"Static planning {num_iteration}",
            **kwargs,
        )


