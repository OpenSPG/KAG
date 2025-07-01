import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_deduce_multi_choice")
class DeduceMutiChoice(PromptABC):
    template_zh = """角色：
你是一个逻辑推理助手，专门根据提供的参考信息从多个选项中选择一个或多个答案来回答问题。

指令：
1. 分析【信息】部分中包含的引用变量（例如：o1, o2）及其问答对；
2. 理解【问题】是否引用了这些变量或与其相关；
3. 基于提供的选项及相关信息，从中选择至少一个选项作为回答；
4. 如果没有任何可选答案，请直接回复“无相关信息”，无需解释。

注意：只能使用给定的信息进行推断，禁止任何假设或自行补充内容。

【信息】：
$memory

【问题】：
$instruction

答案："""
    template_en = """You are a logical reasoning assistant. Please follow these strict instructions:

Analyze the provided [Information] which contains reference variables (e.g., o1, o2) with Q&A pairs.
Evaluate the [Question] which may reference these variables.
Based on the provided options and related variables, choose at least one option to respond to the question
If there are no available options, simply reply 'No relevant information' without explanation.
[Information]:
$memory

[Question]:
$instruction

Answer:"""

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info.startswith("No relevant information"):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("无相关信息"):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
