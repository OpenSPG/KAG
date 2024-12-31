import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RespGenerator(PromptOp):
    template_zh = """
# task
基于给定的信息回答问题。
如果是简单问题，直接说出答案。
如果是复杂问题，给出简洁的解题过程和中间结果，并以正式的口吻总结答案。
如果你无法解答问题，回答：I don't know

# output format
纯文本，不要包含markdown格式。

# context
$memory

# question
$question

# your answer
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "question"]

    def parse_response(self, response: str, **kwargs):
        return response
