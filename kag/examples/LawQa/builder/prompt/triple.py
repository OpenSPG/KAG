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


@PromptABC.register("law_triple")
class OpenIETriplePrompt(PromptABC):
    template_en = """
{
    "instruction": "You are an expert specializing in carrying out open information extraction (OpenIE). Please extract any possible relations (including subject, predicate, object) from the given text, and list them following the json format {\"triples\": [[\"subject\", \"predicate\",  \"object\"]]}. If there are none, do not list them..Pay attention to the following requirements:- Each triple should contain at least one, but preferably two, of the named entities in the entity_list.- Clearly resolve pronouns to their specific names to maintain clarity.",
    "entity_list": $entity_list,
    "input": "$input",
    "example": {
        "input": "The RezortThe Rezort is a 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger. It stars Dougray Scott, Jessica De Gouw and Martin McCann. After humanity wins a devastating war against zombies, the few remaining undead are kept on a secure island, where they are hunted for sport. When something goes wrong with the island's security, the guests must face the possibility of a new outbreak.",
        "entity_list": [
            {
                "name": "The Rezort",
                "category": "Works"
            },
            {
                "name": "2015",
                "category": "Others"
            },
            {
                "name": "British",
                "category": "GeographicLocation"
            },
            {
                "name": "Steve Barker",
                "category": "Person"
            },
            {
                "name": "Paul Gerstenberger",
                "category": "Person"
            },
            {
                "name": "Dougray Scott",
                "category": "Person"
            },
            {
                "name": "Jessica De Gouw",
                "category": "Person"
            },
            {
                "name": "Martin McCann",
                "category": "Person"
            },
            {
                "name": "zombies",
                "category": "Creature"
            },
            {
                "name": "zombie horror film",
                "category": "Concept"
            },
            {
                "name": "humanity",
                "category": "Concept"
            },
            {
                "name": "secure island",
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

    template_zh = """
{
    "instruction": "您是一位专门从事开放信息提取（OpenIE）的专家。请从input字段的文本中提取任何可能的关系（包括主语、谓语、宾语），并按照JSON格式列出它们，须遵循example字段的示例格式。请注意以下要求：1. 每个三元组应至少包含entity_list实体列表中的一个，但最好是两个命名实体。2. 明确地将代词解析为特定名称，以保持清晰度。",
    "entity_list": $entity_list,
    "注意": "如果input中存在法条，则需要拆出`所属法律`和`所属条目`关系"
    "input": "$input",
    "example": {
        "input": "中华人民共和国刑事诉讼法 第五十条 --  可以用于证明案件事实的材料，都是证据。证据包括：（一）物证；（二）书证；（三）证人证言；（四）被害人陈述；（五）犯罪嫌疑人、被告人供述和辩解；（六）鉴定意见；（七）勘验、检查、辨认、侦查实验等笔录；（八）视听资料、电子数据。证据必须经过查证属实，才能作为定案的根据。",
        "entity_list": [
            {"name": "中华人民共和国刑事诉讼法", "category": "LegalName"},
            {"name": "第五十条", "category": "ItemIndex"},
            {"name": "中华人民共和国刑事诉讼法第五十条", "category": "LegalItem"},
            {"name": "物证", "category": "LegalEvidence"},
            {"name": "书证", "category": "LegalEvidence"},
            {"name": "证人证言", "category": "LegalEvidence"},
            {"name": "被害人陈述", "category": "LegalEvidence"},
            {"name": "犯罪嫌疑人、被告人供述和辩解", "category": "LegalEvidence"},
            {"name": "鉴定意见", "category": "LegalEvidence"},
            {"name": "勘验、检查、辨认、侦查实验等笔录", "category": "LegalEvidence"},
            {"name": "视听资料、电子数据。证据必须经过查证属实，才能作为定案的根据", "category": "LegalEvidence"},
        ],
        "output":[
            ["中华人民共和国刑事诉讼法第五十条", "所属法律", "中华人民共和国刑事诉讼法"],
            ["中华人民共和国刑事诉讼法第五十条", "所属条目", "第五十条"],
        ]
    }
}    
    """

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
