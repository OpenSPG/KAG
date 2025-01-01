import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RespGenerator(PromptOp):
    template_zh = """
# 背景知识
$dk

# 问题
$question
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["dk", "question"]

    def parse_response(self, response: str, **kwargs):
        return response
