import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_rewrite_sub_task_query")
class DefaultRewriteSubTaskQueryPrompt(PromptABC):
    template_zh = """{
    "instruction":"请根据上下文的信息，替换当前问题中涉及的指代实体，进而改写当前问题。",
    "cases": [
        {
            "content": {
                "target question": "X先生的老婆的代表作品有哪些"
                "history_qa": [
                "Step1:X先生的老婆是谁？\nanswer:Y女士",
                ]
            }
            "question": "Step1的答案中的人代表作品有哪些？"
            "rewrite question": "Y女士的代表作品有哪些？"
        },
        {
            "content": {
                "target question": "A先生的兄弟们在哪个学校读书"
                "history_qa": [
                "Step1:A先生的兄弟有哪些？\nanswer:A先生的兄弟有B先生、C先生、D先生",
                ]
            }
            "question": "在Step1中检索到的人在哪儿受教育"
            "rewrite question": "B先生、C先生、D先生分别在哪儿受教育"
        },
    ],
    "content": "$content",
    "question": "$input",
    "notice": "不要输出json格式，只使用文本输出改写的问题，并且尽可能完整的输出改写问题，不要遗漏不要输出其他额外信息"
}"""
    template_en = """"{
    "instruction": "Based on the context information, replace the referential entities in the current question, and rewrite the current question.",
    "cases": [
        {
            "content": {
                "target question": "What are the representative works of Mr. X's wife?",
                "history_qa": [
                    "Step1: Who is Mr. X's wife?\nanswer: Ms. Y"
                ]
            },
            "question": "What are the representative works of the person mentioned in Step1's answer?",
            "rewrite question": "What are the representative works of Ms. Y?"
        },
        {
            "content": {
                "target question": "In which school do Mr. A's brothers study?",
                "history_qa": [
                    "Step1: Who are Mr. A's brothers?\nanswer: Mr. A's brothers are Mr. B, Mr. C, and Mr. D"
                ]
            },
            "question": "Where do the people retrieved in Step1 receive education?",
            "rewrite question": "Where do Mr. B, Mr. C, and Mr. D receive education?"
        }
    ],
    "content": "$content",
    "question": "$input",
    "notice": "Do not output json format, only output the rewrite question with text and provide the rewritten question as completely as possible without any additional information."
}
"""

    def is_json_format(self):
        return False

    @property
    def template_variables(self) -> List[str]:
        return ["content", "input"]

    def parse_response(self, response: list, **kwargs):
        logger.debug(f"rewrite sub query:{response}")
        return response
