import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RewriteSubQuestionPrompt(PromptOp):
    template_zh = """
# task
根据给定的前置问题答案，重写子问题。
如果子问题信息已经完整，直接返回原有子问题即可。
改写后的子问题，必须保持信息完整，关键字不能有丢失。

# output format
纯文本，不要包含markdown格式。

# context
$history

$dk

# sub question
$question

# your answer
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["history", "question", "dk"]

    def parse_response(self, response: str, **kwargs):
        return response
