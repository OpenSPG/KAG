from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("resp_simple")
class RespGenerator(PromptABC):
    template_zh = (
        "参考示例,基于给定的引用信息回答问题。" "\n只输出答案，不需要输出额外的信息。" "\n给定的引用信息：'$memory'\n问题：'$instruction'"
        """examples:
        {
            "question": "2岁到青春前期，体重每年增加（　　）。{"A": "0.5kg", "B": "1kg", "C": "1.5kg", "D": "2kg", "E": "2.5kg"}",
            "answer": "D: 2kg"
        }"""
    )
    template_en = (
        "Answer the question based on the given reference."
        "\nOnly give me the answer and do not output any other words."
        "\nThe following are given reference:'$memory'\nQuestion: '$instruction'"
    )

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
