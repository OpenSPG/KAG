from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("resp_simple")
class RespGenerator(PromptABC):
    template_zh = (
        "基于给定的引用信息回答问题。" "\n只输出答案，不需要输出额外的信息。" "\n给定的引用信息：'$content'\n问题：'$query'"
    )
    # template_en = (
    #     "Answer the question based on the given reference."
    #     "\nOnly give me the answer and do not output any other words."
    #     "\nThe following are given reference:'$content'\nQuestion: '$query'"
    # )

    template_en = """
Please Answer the question based on your own knowledge.\n
Your response start after `Thought:` , where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.\n
Question: '$query'    
    """

    @property
    def template_variables(self) -> List[str]:
        return ["query", "content"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        if "Answer:" in response:
            return response.split("Answer: ")[1]
        else:
            return "UNKNOWN"
