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
from typing import List

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC
from knext.schema.client import SchemaClient


@PromptABC.register("musique_ner")
class OpenIENERPrompt(PromptABC):

    template_en = """
    {
    "instruction": "You're a very effective entity extraction system. Please extract all the entities that are important for knowledge build and question, along with type, category and a brief description of the entity. The description of the entity is based on your OWN KNOWLEDGE AND UNDERSTANDING and does not need to be limited to the context. the entity's category belongs taxonomically to one of the items defined by schema, please also output the category. Note: Type refers to a specific, well-defined classification, such as Professor, Actor, while category is a broader group or class that may contain more than one type, such as Person, Works. Return an empty list if the entity type does not exist. Please respond in the format of a JSON string.You can refer to the example for extraction.",
    "schema": $schema,
    "example": [
        {
            "input": "The Rezort\nThe Rezort is a 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger.\n It stars Dougray Scott, Jessica De Gouw and Martin McCann.\n After humanity wins a devastating war against zombies, the few remaining undead are kept on a secure island, where they are hunted for sport.\n When something goes wrong with the island's security, the guests must face the possibility of a new outbreak.",
            "output": [
                        {
                            "entity": "The Rezort",
                            "type": "Movie",
                            "category": "Works",
                            "description": "A 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger."
                        },
                        {
                            "entity": "2015",
                            "type": "Year",
                            "category": "Date",
                            "description": "The year the movie 'The Rezort' was released."
                        },
                        {
                            "entity": "British",
                            "type": "Nationality",
                            "category": "GeographicLocation",
                            "description": "Great Britain, the island that includes England, Scotland, and Wales."
                        },
                        {
                            "entity": "Steve Barker",
                            "type": "Director",
                            "category": "Person",
                            "description": "Steve Barker is an English film director and screenwriter."
                        },
                        {
                            "entity": "Paul Gerstenberger",
                            "type": "Writer",
                            "category": "Person",
                            "description": "Paul is a writer and producer, known for The Rezort (2015), Primeval (2007) and House of Anubis (2011)."
                        },
                        {
                            "entity": "Dougray Scott",
                            "type": "Actor",
                            "category": "Person",
                            "description": "Stephen Dougray Scott (born 26 November 1965) is a Scottish actor."
                        },
                        {
                            "entity": "Jessica De Gouw",
                            "type": "Actor",
                            "category": "Person",
                            "description": "Jessica Elise De Gouw (born 15 February 1988) is an Australian actress. "
                        },
                        {
                            "entity": "Martin McCann",
                            "type": "Actor",
                            "category": "Person",
                            "description": "Martin McCann is an actor from Northern Ireland. In 2020, he was listed as number 48 on The Irish Times list of Ireland's greatest film actors"
                        }
                    ]
        }
    ],
    "input": "$input"
}    
        """

    template_zh = template_en

    def __init__(self, language: str = ""):
        super().__init__(language)
        self.schema = SchemaClient(
            project_id=KAG_PROJECT_CONF.project_id
        ).extract_types()
        self.template = Template(self.template).safe_substitute(schema=self.schema)

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            entities = rsp["named_entities"]
        else:
            entities = rsp

        return entities
