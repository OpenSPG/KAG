from typing import List
import logging

from kag.common.utils import get_now
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_refer_generator_prompt")
class ReferGeneratorPrompt(PromptABC):
    template_zh = (
        f"你是一个信息分析专家，今天是{get_now(language='zh')}。"
        "基于给定的引用信息回答问题。"
        "\n输出答案，如果答案中存在引用信息，则需要reference的id字段，如果不是检索结果，则不需要标记引用"
        "\n输出时，不需要重复输出参考文献"
        '\n引用要求，使用类似<reference id="chunk:1_2"></reference>表示'
        "\n如果根据引用信息无法回答，则使用模型内的知识回答，但是必须通过合适的方式提示用户，是基于检索内容还是引用文档"
        """
示例1：
任务过程上下文：
根据常识岳父是妻子的爸爸，所以需要首先找到张三的妻子，然后找到妻子的爸爸
给定的引用信息：'
reference：
[
{
    "content": "张三 妻子 王五",
    "document_name": "张三介绍",
    "id": "chunk:1_1"
},
{
    "content": "王五 父亲 王四",
    "document_name": "张三介绍",
    "id": "chunk:1_2"
}
]'
问题：'张三的岳父是谁？'

张三的妻子是王五<reference id="chunk:1_1"></reference>，而王五的父亲是王四<reference id="chunk:1_2"></reference>，所以张三的岳父是王四

"""
        "\n输出语调要求通顺，不要有机械感，输出的语言要和问题的语言保持一致"
        "\n任务过程上下文信息：'$content'"
        "\n给定的引用信息：'$ref'\n问题：'$query'"
    )
    template_en = (
        f"You are an information analysis expert, today is {get_now(language='en')}."
        """Answer the question based on the given references.
If the answer contains referenced information, include the `id` field from the reference. If it is not a retrieved result, no citation marker is needed.
Do not repeat the references when outputting the answer.
Citations should be in the format `<reference id="chunk:1_2"></reference>`, and the cited symbol must exist in the `id` field of the references; otherwise, no citation should be provided.
If the question cannot be answered using the given references, use internal model knowledge to respond but clearly indicate whether the response is based on retrieved content or cited documents.

Example 1:
Task Process Context: Based on common knowledge, the father-in-law is the father of one's spouse. Therefore, we first need to find John's spouse, and then find the father of the spouse.
Given references:
reference:
[
    {
        "content": "John's wife is Mary",
        "document_name": "Introduction to John",
        "id": "chunk:1_1"
    },
    {
        "content": "Mary's father is Robert",
        "document_name": "Introduction to John",
        "id": "chunk:1_2"
    }
]
Question: 'Who is John's father-in-law?'

John's wife is Mary <reference id="chunk:1_1"></reference>, and Mary's father is Robert <reference id="chunk:1_2"></reference>. Therefore, John's father-in-law is Robert.

Example 2:
Task Process Context: Based on common knowledge, the father-in-law is the father of one's spouse. Therefore, we first need to find John's spouse, and then find the father of the spouse.
Given references:
reference:
[
    {
        "content": "John's wife is Mary",
        "document_name": "Introduction to John",
        "id": "chunk:1_1"
    },
    {
        "content": "Mary's father is Robert",
        "document_name": "Introduction to John",
        "id": "chunk:1_2"
    }
]
Question: 'John的岳父是谁'

John的妻子是Mary <reference id="chunk:1_1"></reference>, Mary的父亲是Robert <reference id="chunk:1_2"></reference>. 所以John的岳父是Robert.


The tone of the response should be smooth and natural, avoiding any mechanical feel, and the language of the output should match the language of the question.
Task Process Context: '$content'
Given references: '$ref'
Question: '$query'
"""
    )

    @property
    def template_variables(self) -> List[str]:
        return ["content", "query", "ref"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
