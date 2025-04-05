from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_refer_generator_prompt")
class ReferGeneratorPrompt(PromptABC):
    template_zh = (
        "基于给定的引用信息回答问题。"
        "\n输出答案，如果答案中存在引用信息，则需要reference的id字段，如果不是检索结果，则不需要标记引用"
        "\n输出时，不需要重复输出参考文献"
        "\n引用要求，使用类似[chunk:1_1]表示，所引用的符号必须在reference中的id存在，否者不给出引用"
        "\n如果根据引用信息无法回答，先告诉用户，根据检索的内容无法确切知道答案，然后使用模型内的知识回答，，但是必须提示用户是根据模型内知识回答，可能存在知识过期的情况"
        "\n输出语调要求通顺，不要有机械感"
        "\n给定的引用信息：'$content'\n问题：'$query'"
        """
示例1：
给定的引用信息：'
reference：
[
{
    "content": "张三 妻子 王五",
    "document_name": "张三介绍",
    "id": "chunk:1_1"
}
]'
问题：'张三的妻子是谁？'

张三的妻子是王五[chunk:1_1]

示例2：
给定的引用信息：'经过计算器计算，9.2比9.1要大'
问题：'9.1和9.2谁大?'

9.2大
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
