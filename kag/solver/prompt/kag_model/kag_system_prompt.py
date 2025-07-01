import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_system")
class KagSystemPrompt(PromptABC):
    template_zh = """当你回答每一个问题时，你必须提供一个思考过程，并将其插入到<think>和</think>之间"""
    template_en = """As you answer each question, you must provide a thought process and insert it between <think> and </think>."""

    @property
    def template_variables(self) -> List[str]:
        return []

    def parse_response(self, response: str, **kwargs):
        return response
