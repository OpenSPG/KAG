import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_deduce_judge")
class DeduceJudge(PromptABC):
    template_zh = """角色：
你是一个逻辑推理助手，专门根据提供的参考信息判断问题是否成立。

指令：
1. 分析【信息】部分中包含的引用变量（例如：o1, o2）及其问答对；
2. 判断【问题】是否引用了这些变量或与其相关；
3. 仅输出以下三种结果之一：
   - “是”——如果信息确认问题陈述；
   - “否”——如果信息与问题陈述矛盾；
   - “无相关信息”——如果无法根据给定信息作出判断，并请附上理由。

注意：只能使用给定的信息进行判断，禁止任何假设或自行补充内容。

【信息】：
$memory

【问题】：
$instruction

答案："""
    template_en = """You are a logical reasoning assistant. Please follow these strict instructions:

Analyze the provided [Information] which contains reference variables (e.g., o1, o2) with Q&A pairs.
Evaluate the [Question] which may reference these variables.
Output only one of these three values:
Yes if the information confirms the statement in the question
No if the information contradicts the statement
No relevant information if the question cannot be answered with the given data
[Information]:
$memory

[Question]:
$instruction

Answer:
{Output only Yes/No/No relevant information}
"""

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
