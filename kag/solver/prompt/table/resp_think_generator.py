import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RethinkRespGenerator(PromptOp):
    template_zh = """
# task
给定的信息不能够回答问题，你的任务是基于用户给定的问题，思考背后需要获取的信息，并基于已有信息经可能给出一些相关的回答

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
