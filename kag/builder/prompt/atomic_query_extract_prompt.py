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
import json

from typing import List
from kag.interface import PromptABC, Task


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant good at content understanding and asking question."
)


@PromptABC.register("atomic_query_extract")
class AtomicQueryExtractPrompt(PromptABC):
    template_en = """
# Task
Your task is to extract as many questions as possible that are relevant and can be answered by the given content. Please try to be diverse and avoid extracting duplicated or similar questions. Make sure your question contain necessary entity names and avoid to use pronouns like it, he, she, they, the company, the person etc.

# Output Format
Output your answers line by line, with each question on a new line, without itemized symbols or numbers.

# Content
    """

    @property
    def template_variables(self) -> List[str]:
        return ["content"]

    def build_prompt(self, variables) -> str:
        content = variables["content"]
        template = f"{self.template_en}\n{content}\n\n# Output:\n"
        return template

    def parse_response(self, response: str, **kwargs):
        questions = response.split("\n")
        questions = [
            question.strip() for question in questions if len(question.strip()) > 0
        ]
        return questions
