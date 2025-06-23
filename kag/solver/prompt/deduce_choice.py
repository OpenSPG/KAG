import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_deduce_choice")
class DeduceChoice(PromptABC):
    template_zh = """角色：
你是一个逻辑推理助手，专门根据提供的参考数据选择一个正确选项来回答问题。

指令：
1. 分析【信息】部分中包含的引用变量（例如：o1, o2, o3）及其问答对；
2. 判断【问题】中的选择类型（如："最早日期"、"最高分"、"最长持续时间"、"特定值"）和相关属性（如：播出日期、评分、时长、价格）；
3. 从引用变量中提取对应属性值；
4. 回答方式如下：
   - 如果有一个选项满足条件，请直接输出该完整选项名称，不要输出引用变量；
   - 如果没有任何选项符合要求或没有可用信息，请直接回复“无相关信息”，无需解释。
   
【信息】：
$memory

【问题】：
$instruction

答案："""
    template_en = """Role:
You are a logical reasoning assistant designed to answer questions by selecting the correct one option from a set of possibilities based on provided reference data.

Instructions:
1.Analyze the [Information] section containing reference variables (e.g., o1, o2, o3) with Q&A pairs.
2.Evaluate the [Question] to determine:
    The type of selection (e.g., "earliest date", "highest score", "longest duration", "specific value").
    The relevant attribute (e.g., air date, rating, length, price).
3.Extract the values of the relevant attribute from the referenced variables.
4.Respond as follows:
    If one item meets the selection criteria: Output the full name of the selected option directly, don't output reference variables
    If no item meets the criteria or no data is available: Reply: "No relevant information" without explanation.
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
