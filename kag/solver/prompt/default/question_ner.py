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

import json
from string import Template
from typing import List, Optional

from kag.common.base.prompt_op import PromptOp
from kag.schema.client import SchemaClient


class QuestionNER(PromptOp):

    template_en = """
{
    "instruction": "You are an expert in named entity recognition. Please extract all named entities that are important for solving the `input` questions, and gives each entity a category type defined in `schema`. Return an empty list if the entity type does not exist. Please respond in the format of a JSON string and make sure the JSON string syntax is correct. You can refer to the example for extraction.",
    "schema": $schema,
    "example": [
        {
            "input": "Which magazine was started first, Arthur's Magazine or First for Women?",
            "output": [
                {
                    "entity": "First for Women",
                    "category": "Works"
                },
                {
                    "entity": "Arthur's Magazine",
                    "category": "Works"
                }
            ]
        }
    ],
    "input": "$input"
}
"""

#     template_en = """You are an expert in named entity recognition. Please extract entities that matches the Schema defined below from the input.
# Schema: $schema
#
# A Example:
# Question: Which magazine was started first, Arthur's Magazine or First for Women?
# Output: [{"entity": "First for Women", "category": "Works"}, {"entity": "Arthur's Magazine", "category": "Works"}]
#
# Your Question: $input
# Return an empty list if the entity type does not exist.
# Please respond in the format of a JSON string and make sure the JSON string syntax is correct.
# """

#     template_en = """"
# Question: {}
#
# """
#     query_prompt_one_shot_input = """Please extract all named entities that are important for solving the questions below. Place the named entities in json format.
# Question: Which magazine was started first Arthur's Magazine or First for Women?"""
#     query_prompt_one_shot_output = """
# {"named_entities": [{"entity": "First for Women", "category": "Entity"}, {"entity": "Arthur's Magazine", "category": "Entity"}]}
# """

    template_zh = template_en

    # def build_prompt(self, variables) -> str:
    #     from langchain_core.prompts import ChatPromptTemplate
    #     from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    #     query_ner_prompts = ChatPromptTemplate.from_messages(
    #         [SystemMessage("You're a very effective entity extraction system."),
    #         HumanMessage(self.query_prompt_one_shot_input),
    #         AIMessage(self.query_prompt_one_shot_output),
    #         HumanMessage(self.template_en.format(variables['input']))])
    #     query_ner_messages = query_ner_prompts.format_prompt()
    #     return query_ner_messages.to_string()

    def __init__(
            self, language: Optional[str] = "en"
    ):
        super().__init__(language)
        self.schema = SchemaClient().extract_types()
        self.template = Template(self.template).safe_substitute(schema=self.schema)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            if rsp.startswith('AI:'):
                rsp = rsp[3:]
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            entities = rsp["named_entities"]
        elif isinstance(rsp, dict) and "entities" in rsp:
            entities = rsp["entities"]
        else:
            entities = rsp

        return entities
