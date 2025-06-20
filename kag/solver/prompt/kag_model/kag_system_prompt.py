import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_system")
class KagSystemPrompt(PromptABC):
    template_zh = (
        "根据提供的选项及相关答案，请选择其中一个选项回答问题“$instruction”。"
        "无需解释；"
        "如果没有可选择的选项，直接回复“无相关信息”无需解释"
        "注意，只能根据输入的信息进行推断，不允许进行任何假设"
        "\n【信息】：“$memory”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。"
    )
    template_en = """As you answer each question, you must provide a thought process and insert it between <think> and </think>."""

    @property
    def template_variables(self) -> List[str]:
        return []

    def parse_response(self, response: str, **kwargs):
        return response
