import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class SelectDocsPrompt(PromptOp):
    template_zh = """
# instruction
基于问题和召回数据，选择最相关的原文返回。
原文如果是表格，返回表格。
忠实的返回原文文本，不要改动任何一个字。
如果所有数据都与问题无关，返回：I don't know.

# output format
markdown格式

# pay attention
忠实的返回原文文本，不要改动任何一个字。

# question
$question

# recall docs
$docs

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
