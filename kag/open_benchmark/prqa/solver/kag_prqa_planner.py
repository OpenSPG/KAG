import json
import logging

from kag.interface import PlannerABC, LLMClient
from kag.open_benchmark.prqa.solver.prompt.prompt_message import type_messages

logger = logging.getLogger()

type_tools = [{
    "type": "function",
    "function": {
        "name": "get_handle_type",
        "description": "Get which class of problems does analysis belong",
        "parameters": {
            "type": "object",
            "properties": {
                "handle_type": {"type": "number"}
            },
            "required": ["handle_type"],
            "additionalProperties": False
        },
        "strict": True
    }
}]


@PlannerABC.register("kag_prqa_planner")
class PrqaPlanner(PlannerABC):
    """mcp planner that generates task plans using LLM with query rewriting capability.

    Args:
        llm (LLMClient): Language model client for plan generation
    """

    def __init__(self, llm: LLMClient, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    def analyze_question(self, question: str) -> str:
        """问题分类"""
        new_message = {
            "role": "user",
            "content": str(question)
        }
        type_messages.append(new_message)

        completion_1 = self.send_type_messages_deepseek(type_messages)

        tool = completion_1.tool_calls[0]
        args = json.loads(tool.function.arguments)
        handle_type = args.get("handle_type")
        del type_messages[-1]

        if int(handle_type) == 1:
            return 'type1'
        elif int(handle_type) == 2:
            return 'type2'
        elif int(handle_type) == 3:
            return 'type3'
        else:
            logger.error(f"对于问题: {question}\n 大模型处理type错误: {handle_type}\n", exc_info=True)
            return ""

    def send_type_messages_deepseek(self, messages):
        response = self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=messages,
            tools=type_tools
        )
        return response.choices[0].message


