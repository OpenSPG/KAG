import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RetrieverRespGenerator(PromptOp):
    template_zh = "基于给定的引用信息回答问题。" \
                  "\n直接输出答案。" \
                  "\n如果没有合适的答案，请回答“I don't know”。"\
                  "\n给定的引用信息：'$memory'\n问题：'$instruction'"
    template_en = "Answer the question based on the given reference." \
                 "\nGive me the answer." \
                 "\nIf there is no suitable answer, answer 'I don't know'"\
                 "\nThe following are given reference:'$memory'\nQuestion: '$instruction'"

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug('推理器判别:{}'.format(response))
        return response