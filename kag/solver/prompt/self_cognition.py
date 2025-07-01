from typing import List

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import PromptABC


@PromptABC.register("default_self_cognition")
class SelfCognitionPrompt(PromptABC):

    template_zh = """你是KAG(KAG 是基于 OpenSPG 引擎和大型语言模型的逻辑推理问答框架)，你的任务是判断输入的问题“$question”是否是自我认知类问题。
扩展要求：和自我认识相关的扩展问题也算，例如”你的官网是什么“
要求：
直接告诉“是”或者“否”
"""

    template_en = """You are KAG(KAG is a logical reasoning and Q&A framework based on the OpenSPG engine and large language models). Your task is to determine whether the input question “$question” is a self-awareness question.
Extended Requirements: Questions related to self-recognition are also considered, such as "What is your website?"
Requirements:
Directly answer “Yes” or “No”."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
            if self.kag_project_config.language == "en":
                return self.parse_response_en(response)
            return self.parse_response_zh(response)
        except Exception as e:
            print(e)
            return False
