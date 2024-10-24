import logging
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class DeduceEntail(PromptOp):
    template_zh = "根据提供的信息，请首先判断是否能够直接回答指令“$instruction”。如果可以直接回答，请直接回复答案，" \
                  "无需解释；如果不能直接回答但存在关联信息，请总结其中与指令“$instruction”相关的关键信息，并明确解释为何与指令相关；" \
                  "如果没有任何相关信息，直接回复“无相关信息”无需解释。" \
                  "\n【信息】：“$memory”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。"
    template_en = "Based on the provided information, first determine whether you can directly respond to the " \
                  "instruction '$instruction'. If you can directly answer, " \
                  "reply with the answer without any explanation;" \
                  " if you cannot answer directly but there is related information, " \
                  "summarize the key information related to the instruction '$instruction' " \
                  "and clearly explain why it is related; " \
                  "if there is no relevant information, simply reply 'No relevant information' without explanation." \
                  "\n[Information]: '$memory'" \
                  "\nEnsure that the information provided comes directly and accurately from the retrieved document, " \
                  "without any speculation."


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
