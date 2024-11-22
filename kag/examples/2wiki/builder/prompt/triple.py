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
from typing import Optional, List

from kag.interface import PromptABC


@PromptABC.register("2wiki_triple")
class OpenIETriplePrompt(PromptABC):
    template_en = """
{
    "instruction": "You are an expert specializing in carrying out open information extraction (OpenIE). Please extract any possible relations (including subject, predicate, object) from the given text, and list them following the json format {\"triples\": [[\"subject\", \"predicate\",  \"object\"]]}\n. If there are none, do not list them.\n.\n\nPay attention to the following requirements:\n- Each triple should contain at least one, but preferably two, of the named entities in the entity_list.\n- Clearly resolve pronouns to their specific names to maintain clarity.",
    "entity_list": $entity_list,
    "input": "$input",
    "example": {
        "input": "The Rezort\nThe Rezort is a 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger.\n It stars Dougray Scott, Jessica De Gouw and Martin McCann.\n After humanity wins a devastating war against zombies, the few remaining undead are kept on a secure island, where they are hunted for sport.\n When something goes wrong with the island's security, the guests must face the possibility of a new outbreak.",
        "entity_list": [
            {
                "entity": "The Rezort",
                "category": "Works"
            },
            {
                "entity": "2015",
                "category": "Others"
            },
            {
                "entity": "British",
                "category": "GeographicLocation"
            },
            {
                "entity": "Steve Barker",
                "category": "Person"
            },
            {
                "entity": "Paul Gerstenberger",
                "category": "Person"
            },
            {
                "entity": "Dougray Scott",
                "category": "Person"
            },
            {
                "entity": "Jessica De Gouw",
                "category": "Person"
            },
            {
                "entity": "Martin McCann",
                "category": "Person"
            },
            {
                "entity": "zombies",
                "category": "Creature"
            },
            {
                "entity": "zombie horror film",
                "category": "Concept"
            },
            {
                "entity": "humanity",
                "category": "Concept"
            },
            {
                "entity": "secure island",
                "category": "GeographicLocation"
            }
        ],
        "output": [
            [
                "The Rezort",
                "is",
                "zombie horror film"
            ],
            [
                "The Rezort",
                "publish at",
                "2015"
            ],
            [
                "The Rezort",
                "released",
                "British"
            ],
            [
                "The Rezort",
                "is directed by",
                "Steve Barker"
            ],
            [
                "The Rezort",
                "is written by",
                "Paul Gerstenberger"
            ],
            [
                "The Rezort",
                "stars",
                "Dougray Scott"
            ],
            [
                "The Rezort",
                "stars",
                "Jessica De Gouw"
            ],
            [
                "The Rezort",
                "stars",
                "Martin McCann"
            ],
            [
                "humanity",
                "wins",
                "a devastating war against zombies"
            ],
            [
                "the few remaining undead",
                "are kept on",
                "a secure island"
            ],
            [
                "they",
                "are hunted for",
                "sport"
            ],
            [
                "something",
                "goes wrong with",
                "the island's security"
            ],
            [
                "the guests",
                "must face",
                "the possibility of a new outbreak"
            ]
        ]
    }
}    
    """

    def __init__(self, language: Optional[str] = "en"):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["entity_list", "input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "triples" in rsp:
            triples = rsp["triples"]
        else:
            triples = rsp

        standardized_triples = []
        for triple in triples:
            if isinstance(triple, list):
                standardized_triples.append(triple)
            elif isinstance(triple, dict):
                s = triple.get("subject")
                p = triple.get("predicate")
                o = triple.get("object")
                if s and p and o:
                    standardized_triples.append([s, p, o])

        return standardized_triples
