from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_resp_verifier")
class RespVerifier(PromptABC):
    template_zh = (
        "仅根据当前已知的信息，并且不允许进行推理，"
        "你能否完全并准确地回答这个问题'$sub_instruction'?\n已知信息：'$supporting_fact'。"
        "\n如果你能，请直接回复‘是’，并给出问题'$sub_instruction'的答案，无需重复问题；如果不可以，请直接回答'否'。"
    )
    template_en = (
        "Judging based solely on the current known information and without allowing for inference, "
        "are you able to respond completely and accurately to the question '$sub_instruction'? \n"
        "Known information: '$supporting_fact'. If yes, please reply with 'Yes', followed by an accurate response to the question '$sub_instruction', "
        "without restating the question; if no, please reply with 'No' directly."
    )

    @property
    def template_variables(self) -> List[str]:
        return ["sub_instruction", "supporting_fact"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info[:3] == "Yes":
            satisfied = True
        else:
            satisfied = False
        if satisfied:
            satisfied_info = satisfied_info.replace("Yes", "").strip()
            res = "The answer to the Question'{}' is '{}'".format(
                self.template_variables_value["sub_instruction"], satisfied_info
            )
            return res
        return None

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("是"):
            satisfied = True
        else:
            satisfied = False
        if satisfied:
            satisfied_info = satisfied_info.replace("是", "").strip()
            res = "问题'{}' 的答案是 '{}'".format(
                self.template_variables_value["sub_instruction"], satisfied_info
            )
            return res
        return None

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
