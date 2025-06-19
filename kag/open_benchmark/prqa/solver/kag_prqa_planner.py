import json
import logging

from kag.interface import PlannerABC, LLMClient
from kag.open_benchmark.prqa.solver.prompt.prompt_message import type_messages

logger = logging.getLogger()

type_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_handle_type",
            "description": "Get which class of problems does analysis belong",
            "parameters": {
                "type": "object",
                "properties": {"handle_type": {"type": "number"}},
                "required": ["handle_type"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        "strict": True,
    }
]


@PlannerABC.register("kag_prqa_planner")
class PrqaPlanner(PlannerABC):
    """PRQA planner that generates question type using LLM with query capability.

    Args:
        llm (LLMClient): Language model client for plan generation
    """

    def __init__(self, llm: LLMClient, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    def analyze_question(self, question: str, retry_count: int = 0) -> str:
        """问题分类"""
        if retry_count != 0:
            # 遍历查找 type_messages 中的 system instruct 并修改内容
            for message in type_messages:
                if message["role"] == "system":
                    # 动态修改 instruct 内容
                    instruct_content = message["content"]
                    if "上一次的判断错误，请重新思考" not in instruct_content:
                        updated_instruct = (
                            instruct_content.strip() + "\n上一次的判断错误，请重新思考。"
                        )
                        message["content"] = updated_instruct
                    break  # 修改完成后直接退出循环
        new_message = {"role": "user", "content": str(question)}
        type_messages.append(new_message)

        completion_1 = self.send_type_messages(type_messages)

        tool = completion_1.tool_calls[0]
        args = json.loads(tool.function.arguments)
        handle_type = args.get("handle_type")
        del type_messages[-1]

        if int(handle_type) == 1:
            return "type1"
        elif int(handle_type) == 2:
            return "type2"
        elif int(handle_type) == 3:
            return "type3"
        else:
            logger.error(
                f"对于问题: {question}\n 大模型处理type错误: {handle_type}\n",
                exc_info=True,
            )
            return ""

    def send_type_messages(self, messages):
        response = self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=messages,
            tools=type_tools,
            tool_choice={"type": "function", "function": {"name": "get_handle_type"}},
        )
        return response.choices[0].message
