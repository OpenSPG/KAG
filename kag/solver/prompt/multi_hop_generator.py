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


@PromptABC.register("default_multi_hop_generator")
class MultiHopGeneratorPrompt(PromptABC):

    template_en = """As an advanced reading comprehension assistant, your task is to answer complex multi-hop questions based on the context I provide. The context I offer includes two parts: a set of documents that are helpful for answering the question, and a step-by-step breakdown of the question along with an analytical thought process. Please combine these two parts of the context to answer the question. Your response start after "Thought: ", where you will methodically break down the reasoning process step by step, illustrating how you arrive at conclusions. Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.\n
NOTE:
1. Directly quote verbatim when the answer exists in Docs.
2. Inferred answers must be based on document content and cannot fabricate information.
3. I hope your answer matches the answer exactly, so ENSURE that the answer following "Answer:" is concise, such as 14 May, 1832  or yes. THE SHORTER, THE BETTER!!
4. If the answer is a date, please provide the full date as much as possible, such as 18 May, 1932.3. Pay attention to the differences in part of speech, such as "Japan" and "Japanese," and provide the accurate format according to the question.
5. If you believe the provided documents cannot answer the question, response with Answer: UNKNOWN.
6. output format use json, like
{
    "thought": "xxxxx",
    "answer": "yyyyy"
}
$content

$query
"""
    template_zh = template_en

    @property
    def template_variables(self) -> List[str]:
        return ["content", "query"]

    def is_json_format(self):
        return True

    def parse_response(self, response: dict, **kwargs):

        if "answer" not in response.keys():
            raise ValueError(f"no answer found in response: {response}")
        return response["answer"]
