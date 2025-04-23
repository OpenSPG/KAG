from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("resp_simple")
class RespGenerator(PromptABC):
    template_zh = (
        "基于给定的引用信息回答问题。" "\n只输出答案，不需要输出额外的信息。" "\n给定的引用信息：'$memory'\n问题：'$instruction'"
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
