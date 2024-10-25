import re
from string import Template
from typing import List
import logging

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class RespJudge(PromptOp):
    template_zh = "根据当前已知信息进行判断，不允许进行推理，" \
                  "你能否完全并准确地回答这个问题'$instruction'?\n已知信息：'$memory'。" \
                  "\n如果你能，请直接回复‘是’\n如果不能且需要更多信息，请直接回复‘否’。"
    template_en = "Judging based solely on the current known information and without allowing for inference, " \
                  "are you able to completely and accurately respond to the question '$instruction'? " \
                  "\nKnown information: '$memory'. " \
                  "\nIf you can, please reply with 'Yes' directly; " \
                  "if you cannot and need more information, please reply with 'No' directly."

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info[:3] == 'Yes':
            if_finished = True
        else:
            if_finished = False
        return if_finished

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("是"):
            if_finished = True
        else:
            if_finished = False
        return if_finished

    def parse_response(self, response: str, **kwargs):
        logger.debug('推理器判别:{}'.format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
