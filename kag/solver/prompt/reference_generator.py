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
        "\n如果根据引用信息无法回答，则使用模型内的知识回答，但是必须通过合适的方式提示用户，是基于检索内容还是引用文档"
        "\n输出语调要求通顺，不要有机械感"
        "\n任务过程上下文信息：'$content'"
        "\n给定的引用信息：'$ref'\n问题：'$query'"
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
"""Answer the question based on the given references.
If the answer contains referenced information, include the `id` field from the reference. If it is not a retrieved result, no citation marker is needed.
Do not repeat the references when outputting the answer.
Citations should be in the format `[chunk:1_1]`, and the cited symbol must exist in the `id` field of the references; otherwise, no citation should be provided.
If the question cannot be answered using the given references, use internal model knowledge to respond but clearly indicate whether the response is based on retrieved content or cited documents.
The tone of the response should be smooth and natural, avoiding any mechanical feel.
Task process contextual information: '$content'
Given references: '$ref'
Question: '$query'

Example 1:
Given references:
reference:
[
    {
        "content": "John's wife is Mary",
        "document_name": "Introduction to John",
        "id": "chunk:1_1"
    }
]
Question: 'Who is John's wife?'

John's wife is Mary [chunk:1_1].

Example 2:
Given references: 'After calculation by the calculator, 9.2 is greater than 9.1.'
Question: 'Which is larger, 9.1 or 9.2?'

9.2 is larger."""
    )

    @property
    def template_variables(self) -> List[str]:
        return ["content", "query", "ref"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
