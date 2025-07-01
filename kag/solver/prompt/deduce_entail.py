import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_deduce_entail")
class DeduceEntail(PromptABC):
    template_zh = """角色：
你是一个逻辑推理助手，专门基于提供的参考信息进行判断并回答问题。

指令：
1. 分析【信息】部分中包含的引用变量（例如：o1, o2）及其问答对；
2. 理解【问题】是否引用了这些变量或与其相关；
3. 按照以下规则进行分析与回答：
   - 如果可以直接回答，请直接输出答案，不要解释；
   - 如果不能直接回答但存在关联信息，请总结与问题相关的关键信息，并明确说明其相关性；
   - 如果没有任何相关信息，请直接回复“无相关信息”，不要解释。
   
注意：只能使用给定的信息进行推断，禁止任何假设或自行补充内容。

【信息】：
$memory

【问题】：
$instruction

答案："""
    template_en = """You are a logical reasoning assistant. Please follow these strict instructions:

Analyze the provided [Information] which contains reference variables (e.g., o1, o2) with Q&A pairs.
Evaluate the [Question] which may reference these variables.
Analyze with rules:
1.If you can directly answer, reply with the answer without any explanation
2.If you cannot answer directly but there is related information, summarize the key information related to the question and clearly explain why it is related
3.If there is no relevant information, reply begin with 'No relevant information' and with explanation
[Information]:
$memory

[Question]:
$instruction

Answer:"""

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info.startswith("No relevant information"):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("无相关信息"):
            if_answered = False
        else:
            if_answered = True
        return if_answered, satisfied_info

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        if self.language == "en":
            return self.parse_response_en(response)
        return self.parse_response_zh(response)
