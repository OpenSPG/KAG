from typing import List

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC


@PromptABC.register("default_self_cognition")
class SelfCognitionPrompt(PromptABC):

    template_zh = """你是一个AI助手，你的任务是判断输入的问题“$question”是否是自我认知类问题。
扩展要求：和自我认识相关的扩展问题也算，例如”你的官网是什么“
要求：
直接告诉“是”或者“否”
"""

    template_en = """You are an AI assistant. Your task is to determine whether the input question “$question” is a self-awareness question.
Extended Requirements: Questions related to self-recognition are also considered, such as "What is your website?"
Requirements:
Directly answer “Yes” or “No”."""

    @property
    def template_variables(self) -> List[str]:
        return ["question"]

    def parse_response_en(self, response: str, **kwargs):
        if "yes" in response.lower():
            return True
        return False

    def parse_response_zh(self, response: str, **kwargs):
        if "是" in response:
            return True
        return False

    def parse_response(self, response: str, **kwargs):
        try:
            response = response.strip()
            if KAG_PROJECT_CONF.language == "en":
                return self.parse_response_en(response)
            return self.parse_response_zh(response)
        except Exception as e:
            print(e)
            return False
