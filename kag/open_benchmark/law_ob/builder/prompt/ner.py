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


@PromptABC.register("law_ner")
class OpenIENERPrompt(PromptABC):
    template_en = """
    {
    "instruction": "You're a very effective entity extraction system. Please extract all the entities that are important for knowledge build and question, along with type, category and a brief description of the entity. The description of the entity is based on your OWN KNOWLEDGE AND UNDERSTANDING and does not need to be limited to the context. the entity's category belongs taxonomically to one of the items defined by schema, please also output the category. Note: Type refers to a specific, well-defined classification, such as Professor, Actor, while category is a broader group or class that may contain more than one type, such as Person, Works. Return an empty list if the entity type does not exist. Please respond in the format of a JSON string.You can refer to the example for extraction.",
    "schema": $schema,
    "example": [
        {
            "input": "The Rezort is a 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger. It stars Dougray Scott, Jessica De Gouw and Martin McCann. After humanity wins a devastating war against zombies, the few remaining undead are kept on a secure island, where they are hunted for sport. When something goes wrong with the island's security, the guests must face the possibility of a new outbreak.",
            "output": [
                        {
                            "name": "The Rezort",
                            "type": "Movie",
                            "category": "Works",
                            "description": "A 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger."
                        },
                        {
                            "name": "2015",
                            "type": "Year",
                            "category": "Date",
                            "description": "The year the movie 'The Rezort' was released."
                        },
                        {
                            "name": "British",
                            "type": "Nationality",
                            "category": "GeographicLocation",
                            "description": "Great Britain, the island that includes England, Scotland, and Wales."
                        },
                        {
                            "name": "Steve Barker",
                            "type": "Director",
                            "category": "Person",
                            "description": "Steve Barker is an English film director and screenwriter."
                        },
                        {
                            "name": "Paul Gerstenberger",
                            "type": "Writer",
                            "category": "Person",
                            "description": "Paul is a writer and producer, known for The Rezort (2015), Primeval (2007) and House of Anubis (2011)."
                        },
                        {
                            "name": "Dougray Scott",
                            "type": "Actor",
                            "category": "Person",
                            "description": "Stephen Dougray Scott (born 26 November 1965) is a Scottish actor."
                        },
                        {
                            "name": "Jessica De Gouw",
                            "type": "Actor",
                            "category": "Person",
                            "description": "Jessica Elise De Gouw (born 15 February 1988) is an Australian actress. "
                        },
                        {
                            "name": "Martin McCann",
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

    template_zh = """
    {
        "instruction": "你是命名实体识别的专家。请从输入中提取与模式定义匹配的实体。如果不存在该类型的实体，请返回一个空列表。请以JSON字符串格式回应。你可以参照example进行抽取。",
        "example": [
            {
                "input": "最高人民法院、最高人民检察院关于办理寻衅滋事刑事案件适用法律若干问题的解释  第一条
最高人民法院、最高人民检察院关于办理寻衅滋事刑事案件适用法律若干问题的解释 第一条 --  行为人为寻求刺激、发泄情绪、逞强耍横等，无事生非，实施刑法第二百九十三条规定的行为的，应当认定为“寻衅滋事”。
行为人因日常生活中的偶发矛盾纠纷，借故生非，实施刑法第二百九十三条规定的行为的，应当认定为“寻衅滋事”，但矛盾系由被害人故意引发或者被害人对矛盾激化负有主要责任的除外。
行为人因婚恋、家庭、邻里、债务等纠纷，实施殴打、辱骂、恐吓他人或者损毁、占用他人财物等行为的，一般不认定为“寻衅滋事”，但经有关部门批评制止或者处理处罚后，继续实施前列行为，破坏社会秩序的除外。",
                "output": [
                        {
                            "name": "最高人民法院",
                            "type": "LegalSubject",
                            "category": "LegalSubject",
                            "description": "中华人民共和国的最高审判机关。"
                        },
                        {
                            "name": "最高人民检察院",
                            "type": "LegalSubject",
                            "category": "LegalSubject",
                            "description": "中华人民共和国的最高检察机关。"
                        },
                        {
                            "name": "寻衅滋事",
                            "type": "Keyword",
                            "category": "Keyword",
                            "description": "指行为人为了寻求刺激、发泄情绪、逞强耍横等，无事生非或者借故生非的行为。"
                        },
                        {
                            "name": "认定为“寻衅滋事”",
                            "type": "LegalConsequence",
                            "category": "LegalConsequence",
                            "description": "根据特定行为判断是否构成寻衅滋事罪的结果。"
                        },
                        {
                            "name": "日常生活中的偶发矛盾纠纷",
                            "type": "Concept",
                            "category": "Concept",
                            "description": "日常生活中发生的偶然性冲突或争执。"
                        },
                        {
                            "name": "婚恋、家庭、邻里、债务等纠纷",
                            "type": "Concept",
                            "category": "Concept",
                            "description": "涉及婚姻、恋爱关系、家庭成员间、邻居之间以及债权债务等方面的争议。"
                        },
                        {
                            "name": "殴打、辱骂、恐吓他人或者损毁、占用他人财物",
                            "type": "LegalAction",
                            "category": "LegalAction",
                            "description": "具体描述了可能构成违法行为的行为方式。"
                        },
                        {
                            "name": "有关部门批评制止或者处理处罚后",
                            "type": "LegalAction",
                            "category": "LegalAction",
                            "description": "相关机构对不当行为采取的干预措施。"
                        },
                        {
                            "name": "破坏社会秩序",
                            "type": "LegalAction",
                            "category": "LegalAction",
                            "description": "行为导致公共安全和社会正常运作受到影响的结果。"
                        }
                    ]

            }
        ],,
        "input": "$input"
    }    
        """

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)
        self.template = Template(self.template).safe_substitute(
            schema="",
        )

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
