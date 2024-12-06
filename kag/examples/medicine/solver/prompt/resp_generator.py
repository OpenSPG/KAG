import re
from string import Template
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("example_resp_generator")
class RespGenerator(PromptABC):
    template_zh = "基于给定的引用信息完整回答问题。" "\n给定的引用信息：'$memory'\n问题：'$instruction'"
    template_en = (
        "Answer the question completely based on the given reference."
        "\nThe following are given reference:'$memory'\nQuestion: '$instruction'"
    )

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
