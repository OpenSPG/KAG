import re
from string import Template
from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_llm_generator_prompt")
class FinalGeneratorPrompt(PromptABC):
    template_zh = (
        "基于给定的引用信息回答问题。"
        "\n输出答案，并且给出理由。并且在答案中引用reference的id字段"
        "\n输出时，不需要重复输出参考文献"
        "\n给定的引用信息：'$content'\n问题：'$query'"
        """示例：
张三的妻子是谁？
reference：
[
{
    "content": "张三 妻子 王五",
    "document_name": "张三介绍",
    "id": "chunk:1_1"
}
]

张三的妻子是王五[chunk:1_1]
"""
    )
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
