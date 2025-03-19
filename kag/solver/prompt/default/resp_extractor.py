from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_resp_extractor")
class RespExtractor(PromptABC):
    template_zh = (
        "已知信息：\n$supporting_fact\n"
        "你的任务是作为一名专业作家。你将仅根据提供的支持段落中的信息，撰写一段高质量的文章，以支持关于问题的给定预测。"
        "现在，开始生成。在写完后，请输出[DONE]来表示已经完成任务。在生成段落时不要写前缀（例如：'Response：'）。"
        "\n问题：$instruction\n段落："
    )
    template_en = (
        "Known information:\n $supporting_fact\nYour job is to act as a professional writer. "
        "You will write a good-quality passage that can support the given prediction about the question only based on the information in the provided supporting passages. "
        "Now, let's start. After you write, please write [DONE] to indicate you are done. Do not write a prefix (e.g., 'Response:'') while writing a passage.\nQuestion:$instruction\nPassage:"
    )

    @property
    def template_variables(self) -> List[str]:
        return ["supporting_fact", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response
