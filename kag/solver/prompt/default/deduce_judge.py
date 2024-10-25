import logging
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class DeduceJudge(PromptOp):
    template_zh = "根据提供的信息，请首先判断是否能够直接判断问题“$instruction”。如果可以直接回答，请直接根据提供信息对问题给出判断是或者否，" \
                  "无需解释；" \
                  "如果没有任何相关信息，直接回复“无相关信息”无需解释。" \
                  "\n【信息】：“$memory”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。" \
                  "\n【问题】：“$instruction”"
    template_en = "Based on the provided information, first determine if the question '$instruction' can be directly assessed. " \
                  "If it can be directly answered, simply respond with Yes or No based on the provided information, no explanation needed;" \
                  "If there is no relevant information, simply reply 'No relevant information' without explanation." \
                  "\n[Information]: '$memory'" \
                  "\nEnsure that the information provided comes directly and accurately from the retrieved document, " \
                  "without any speculation."\
                  "\n[Question]: '$instruction'"


    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info.startswith('No relevant information'):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("无相关信息"):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response(self, response: str, **kwargs):
        logger.debug('推理器判别:{}'.format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
