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
答案要包含上下文信息，使得没有任何背景的人也能理解。
不要尝试进行数值单位换算，忠实的按照原文输出数值，带上单位和变量。
如果基于给定的信息，无法给出答案，那么回答：I don't know.

# output format
纯文本，不要包含markdown格式。

# context
$docs

# question
$question

# your answer
"""
    template_en = template_zh

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["docs", "question"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
