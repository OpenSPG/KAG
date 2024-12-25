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
如果是复杂问题，给出解题过程和中间结果，以正式的口吻给出答案。

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
        logger.debug("推理器判别:{}".format(response))
        return response
