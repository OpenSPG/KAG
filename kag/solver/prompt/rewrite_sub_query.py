import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_rewrite_sub_query")
class DefaultRewriteSubQuery(PromptABC):
    template_zh = """{
    "instruction":"请根据历史对话中的信息，替换当前问题中涉及的指代实体，进而改写当前问题。",
    "cases": [
        {
            "history_qa": "X先生的老婆是谁？\nanswer:Y女士",
            "question": "X先生的老婆的代表作品有哪些？"
            "answer": "Y女士的代表作品有哪些？"
        }
    ],
    "history_qa": "$history_qa",
    "question": "$question",
    "notice": "请直接输出改写后的问题，不要输出推理过程等其他内容。"
}"""
    template_en = """"{
    instruction": "Please rewrite the current question based on historical Q&A information and complete the entities referred to in the question.",
    "cases": [
        {
            "history_qa": "Who is the director of God'S Gift To Women?  \nanswer: Michael Curtiz\nWho is the director of Aldri Annet Enn Bråk?  \nanswer: Edith Carlmar",
            "question": "What is the birth year of the director of God'S Gift To Women? "
            "answer": "What is the birth year of Michael Curtiz"
        },
        {
            "history_qa": "Who is the director of God'S Gift To Women?  \nanswer: Michael Curtiz\nWhat is the birth year of the director of God'S Gift To Women?  \nanswer: 1886\nWho is the director of Aldri Annet Enn Bråk?  \nanswer: Edith Carlmar",
            "question": "What is the birth year of the director of Aldri Annet Enn Bråk? "
            "answer": "What is the birth year of Edith Carlmar"
        }
    ],
    "output_format": "only output re-writed question",
    "history_qa": "$history_qa",
    "question": "$question"
}
"""

    @property
    def template_variables(self) -> List[str]:
        return ["history_qa", "question"]

    def parse_response(self, response: str, **kwargs):
        logger.debug(f"rewrite sub query:{response}")
        return response
