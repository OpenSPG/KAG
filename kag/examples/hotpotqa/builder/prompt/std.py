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
from typing import List


from kag.interface import PromptABC


@PromptABC.register("hotpotqa_std")
class OpenIEEntitystandardizationdPrompt(PromptABC):
    template_en = """
{
    "instruction": "The `input` field contains a user provided context. The `named_entities` field contains extracted named entities from the context, which may be unclear abbreviations, aliases, or slang. To eliminate ambiguity, please attempt to provide the official names of these entities based on the context and your own knowledge. Note that entities with the same meaning can only have ONE official name. Please respond in the format of a single JSONArray string without any explanation, as shown in the `output` field of the provided example.",
    "example": {
        "input": "American History\nWhen did the political party that favored harsh punishment of southern states after the Civil War, gain control of the House? Republicans regained control of the chamber they had lost in the 2006 midterm elections.",
        "named_entities": [
            {"entity": "American", "category": "GeographicLocation"},
            {"entity": "political party", "category": "Organization"},
            {"entity": "southern states", "category": "GeographicLocation"},
            {"entity": "Civil War", "category": "Keyword"},
            {"entity": "House", "category": "Organization"},
            {"entity": "Republicans", "category": "Organization"},
            {"entity": "chamber", "category": "Organization"},
            {"entity": "2006 midterm elections", "category": "Date"}
        ],
        "output": [
            {
                "entity": "American",
                "category": "GeographicLocation",
                "official_name": "United States of America"
            },
            {
                "entity": "political party",
                "category": "Organization",
                "official_name": "Radical Republicans"
            },
            {
                "entity": "southern states",
                "category": "GeographicLocation",
                "official_name": "Confederacy"
            },
            {
                "entity": "Civil War",
                "category": "Keyword",
                "official_name": "American Civil War"
            },
            {
                "entity": "House",
                "category": "Organization",
                "official_name": "United States House of Representatives"
            },
            {
                "entity": "Republicans",
                "category": "Organization",
                "official_name": "Republican Party"
            },
            {
                "entity": "chamber",
                "category": "Organization",
                "official_name": "United States House of Representatives"
            },
            {
                "entity": "midterm elections",
                "category": "Date",
                "official_name": "United States midterm elections"
            }
        ]
    },
    "input": "$input",
    "named_entities": $named_entities
}
    """

    template_zh = """"""

    @property
    def template_variables(self) -> List[str]:
        return ["input", "named_entities"]

    def parse_response(self, response: str, **kwargs):

        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            standardized_entity = rsp["named_entities"]
        else:
            standardized_entity = rsp
        entities_with_offical_name = set()
        merged = []
        entities = kwargs.get("named_entities", [])
        for entity in standardized_entity:
            merged.append(entity)
            entities_with_offical_name.add(entity["entity"])
        # in case llm ignores some entities
        for entity in entities:
            if entity["entity"] not in entities_with_offical_name:
                entity["official_name"] = entity["entity"]
                merged.append(entity)
        return merged
