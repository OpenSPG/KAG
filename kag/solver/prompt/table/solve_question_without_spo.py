from string import Template
from typing import List

from kag.common.base.prompt_op import PromptOp


class SolveQuestionWithOutSPO(PromptOp):

    template_zh = """请根据检索到的相关文档回答问题“$question”，并结合历史信息进行综合分析。
要求：
1.尽可能简洁的回答问题。
2.如果答案是数值，尽可能将数值的约束纬度描述清楚，特别是时间，度量单位，量纲等。
3.如果没有合适的答案，请回答“I don't know”。
历史：
$history
文档：
$docs

答案：
"""

    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "docs"]

    def parse_response(self, response: str, **kwargs):
        return response
