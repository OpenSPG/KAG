# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
# flake8: noqa
from typing import List
from kag.interface import PromptABC


@PromptABC.register("default_thought_then_answer")
class ThoughtThenAnswerPrompt(PromptABC):

    template_en = """As an adept specialist in resolving intricate multi-hop questions, I require your assistance in addressing a multi-hop question. The question has been segmented into multiple straightforward single-hop inquiries, wherein each question may depend on the responses to preceding questions, i.e., the question body may contain content such as "{{i.output}}", which means the answer of ith sub-question. I will furnish you with insights on how to address these preliminary questions, or the answers themselves, which are essential for accurate resolution. Furthermore, I will provide textual excerpts pertinent to the current question, which you are advised to peruse and comprehend thoroughly.

NOTE: If the provided information does not directly answer the question, you must use your internal knowledge in combination with reasoning to derive a reasonable answer.

Begin your reply with "Thought: ", where you'll outline the step-by-step thought process that leads to your conclusion. End with "Answer: " to deliver a clear and precise response without any extra commentary.

Docs:
Sylvester
Sylvester is a name derived from the Latin adjective silvestris meaning ``wooded ''or`` wild'', which derives from the noun silva meaning ``woodland ''. Classical Latin spells this with i. In Classical Latin y represented a separate sound distinct from i, not a native Latin sound but one used in transcriptions of foreign words. After the Classical period y came to be pronounced as i. Spellings with Sylv - in place of Silv - date from after the Classical period.

Stanton Township, Champaign County, Illinois
Stanton Township is a township in Champaign County, Illinois, USA. As of the 2010 census, its population was 505 and it contained 202 housing units.


Montebello, New York
Montebello (Italian: "Beautiful mountain") is an incorporated village in the town of Ramapo, Rockland County, New York, United States. It is located north of Suffern, east of Hillburn, south of Wesley Hills, and west of Airmont. The population was 4,526 at the 2010 census

Erik Hort
Erik Hort (born February 16, 1987 in Montebello, New York) is an American soccer player who is currently a Free Agent.


Questions:
Step1: Who was crowned emperor of the west in 800 CE?
Thought: One of the provided passage on Charlemagne indicates that he was crowned Holy Roman Emperor in 800. Answer: Charlemagne.

Step2: What was Charlemagne later known as?
Thought: To determine what Charlemagne was later known as, I need to review the provided passage about Charlemagne. The passage indicates that Charlemagne was also known as "Charles the Great." Answer: Charles the Great

Step3: What was the language from which the last name Sylvester originated during Charles the Great era?
Thought: The question asks about the origin of the last name Sylvester during the time of the person Charles the Great, which was Charlemagne, whose reign was in the Early Middle Ages. The passage about the name Sylvester states that it is derived from Latin. Answer: Latin

Docs:
$docs

Questions:
$questions

$cur_question
"""
    template_zh = """作为一位擅长解决复杂多跳问题的专家，我需要你的帮助来解决一个多跳问题。该问题已被分割成多个简单的单跳查询，其中每个问题可能依赖于前面问题的回答。我会提供有关如何解决这些初步问题的见解，或者直接提供答案，这些对于准确解答至关重要。此外，我将提供与当前问题相关的文本摘录，建议你仔细阅读并理解这些内容。

注意：如果提供的信息无法直接回答问题，请结合你的内部知识和逻辑推理得出一个合理的答案。

请以“思考: ”开头，概述你的逐步思考过程，以得出结论。以“结论: ”结尾，提供一个清晰且精确的回答，不要包含额外的评论。

文档：
Sylvester
Sylvester 是一个源自拉丁形容词 silvestris 的名字，意为“有树林的”或“野生的”，该形容词来源于名词 silva，意为“树林”。古典拉丁语中拼写为 silvestris，其中 y 表示一个与 i 不同的独立音，不是原生拉丁语音，而是用于外来词的转写。古典时期之后，y 的发音变为 i。Sylv- 的拼写形式出现在古典时期之后。

Stanton Township, Champaign County, Illinois
Stanton Township 是美国伊利诺伊州尚佩恩县的一个镇。根据2010年人口普查，其人口为505人，包含202个住房单元。

Montebello, New York
Montebello（意大利语：“美丽的山”）是美国纽约州罗克兰县拉马波镇的一个注册村庄。它位于 Suffern 以北，Hillburn 以东，Wesley Hills 以南，Airmont 以西。根据2010年人口普查，其人口为4,526人。

Erik Hort
Erik Hort（1987年2月16日出生于纽约州蒙特贝洛）是一名美国职业足球运动员，目前是一名自由球员。

问题：
Step1: 800年谁被加冕为西罗马帝国皇帝？
思考: 提供的关于查理曼大帝的文档指出，他在800年被加冕为神圣罗马帝国皇帝。结论: 查理曼大帝。

Step2: 查理曼大帝后来被称为什么？
思考: 为了确定查理曼大帝后来被称为什么，我需要回顾关于查理曼大帝的文档。文档指出，查理曼大帝还被称为“查理大帝”。结论: 查理大帝

Step3: 查理大帝统治时期，Sylvester 这个姓氏源自哪种语言？
思考: 问题询问查理大帝统治时期（即查理曼大帝的统治时期，属于早期中世纪）Sylvester 这个姓氏的起源。关于名字 Sylvester 的文档指出，它源自拉丁语。结论: 拉丁语

文档：
$docs

问题：
$questions

$cur_question
"""

    @property
    def template_variables(self) -> List[str]:
        return ["docs", "cur_question", "questions"]

    def parse_response(self, response: str, **kwargs):
        return response
