from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("resp_riskmining")
class RespGenerator(PromptABC):
    template_zh = "基于给定的引用信息回答问题。" "\n输出答案，并且给出理由。" "\n给定的引用信息：'$content'\n问题：'$query'"
    template_en = (
        "Answer the question based on the given reference."
        "\nGive me the answer and why."
        "\nThe following are given reference:'$content'\nQuestion: '$query'"
    )

    @property
    def template_variables(self) -> List[str]:
        return ["content", "query"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
