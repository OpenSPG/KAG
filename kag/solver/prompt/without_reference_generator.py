from typing import List
import logging

from kag.common.utils import get_now
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_without_refer_generator_prompt")
class WithOutReferGeneratorPrompt(PromptABC):
    template_zh = (
        f"你是一个信息分析专家，今天是{get_now(language='zh')}。"
        "基于给定的上下文信息回答问题。"
        """
示例1：
任务过程上下文：
'经过计算器计算，9.2比9.1要大'
给定的引用信息：'无'
问题：'9.1和9.2谁大?'

9.2大
"""
        "\n输出语调要求通顺，不要有机械感, 输出的语言要和问题的语言保持一致"
        "\n任务过程上下文信息：'$content'"
        "\n问题：'$query'"
    )
    template_en = (
        f"You are an information analysis expert, today is {get_now(language='en')}."
        """Answer the question based on the given context.
Do not repeat the references when outputting the answer.

Example 1:
Task Process Context: 'After calculation by the calculator, 9.2 is greater than 9.1.'
Given references: ''
Question: 'Which is larger, 9.1 or 9.2?'
Answer: 9.2 is larger.

The tone of the response should be smooth and natural, avoiding any mechanical feel, and the language of the output should match the language of the question.
Task process contextual information: '$content'
Question: '$query'

"""
    )

    @property
    def template_variables(self) -> List[str]:
        return ["content", "query", "ref"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
