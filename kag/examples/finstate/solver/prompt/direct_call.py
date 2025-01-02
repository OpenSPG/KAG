import logging
import re
from string import Template
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)

from kag.common.base.prompt_op import PromptOp


class DirectCall(PromptOp):

    template_zh = """$input"""

    template_en = """$input"""

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]


    def parse_response(self, response: str, **kwargs):
        return response
