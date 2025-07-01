import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_resp_reflector")
class RespReflector(PromptABC):
    template_zh = (
        "你是一个智能助手，擅长通过复杂的、多跳的推理帮助用户在多文档中获取信息。请理解当前已知信息与目标问题之间的信息差。"
        "你的任务是直接生成一个用于下一步检索的思考问题。"
        "不要一次性生成所有思考过程！\n[已知信息]： $memory\n[目标问题]：$instruction\n[你的思考]："
    )
    template_en = (
        "You serve as an intelligent assistant, adept at facilitating users through complex, "
        "multi-hop reasoning across multiple documents. Please understand the information gap between the currently known information and the target problem."
        "Your task is to generate one thought in the form of question for next retrieval step directly. "
        "DON'T generate the whole thoughts at once!\n[Known information]: $memory\n[Target question]: $instruction\n[You Thought]:"
    )

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response_en(self, response: str):
        update_reason_path = []
        split_path = response.split("\n")
        for p in split_path:
            if "Here are the steps" in p or p == "\n" or p == "":
                continue
            else:
                update_reason_path.append(p)
        logger.debug("cur path:{}".format(str(update_reason_path)))
        return update_reason_path

    def parse_response_zh(self, response: str):
        update_reason_path = []
        split_path = response.split("\n")
        for p in split_path:
            if "步骤为" in p or p == "\n" or p == "":
                continue
            else:
                update_reason_path.append(p)
        logger.debug("cur path:{}".format(str(update_reason_path)))
        return update_reason_path

    def parse_response(self, response: str, **kwargs):
        logger.debug("infer result:{}".format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
