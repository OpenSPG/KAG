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

    template_en = """As an adept specialist in resolving intricate multi-hop questions, I require your assistance in addressing a multi-hop question. The question has been segmented into multiple straightforward single-hop inquiries, wherein each question may depend on the responses to preceding questions, i.e., the question body may contain content such as "{{i.output}}", which means the answer of ith sub-question. I will furnish you with insights on how to address these preliminary questions, or the answers themselves, which are essential for accurate resolution. Furthermore, I will provide textual excerpts pertinent to the current question, which you are advised to peruse and comprehend thoroughly. Begin your reply with "Thought: ", where you'll outline the step-by-step thought process that leads to your conclusion. End with "Answer: " to deliver a clear and precise response without any extra commentary.

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
    template_zh = template_en

    @property
    def template_variables(self) -> List[str]:
        return ["docs", "cur_question", "questions"]

    def parse_response(self, response: str, **kwargs):
        return response
