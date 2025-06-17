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
from kag.interface import PromptABC
from knext.schema.client import SchemaClient
from knext.schema.model.base import SpgTypeEnum


@PromptABC.register("default_ner")
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
        "schema": $schema,
        "example": [
            {
                "input": "《Rezort》是一部 2015年英国僵尸恐怖片，由史蒂夫·巴克执导，保罗·格斯滕伯格编剧。该片由道格瑞·斯科特、杰西卡·德·古维和马丁·麦凯恩主演。在人类赢得与僵尸的毁灭性战争后，剩下的少数不死生物被关在一个安全的岛屿上，在那里他们被猎杀作为消遣。当岛上的安全出现问题时，客人们必须面对新一轮疫情爆发的可能性。",
                "output": [
                            {
                                "name": "The Rezort",
                                "type": "Movie",
                                "category": "Works",
                                "description": "一部 2015 年英国僵尸恐怖片，由史蒂夫·巴克执导，保罗·格斯滕伯格编剧。"
                            },
                            {
                                "name": "2015",
                                "type": "Year",
                                "category": "Date",
                                "description": "电影《The Rezort》上映的年份。"
                            },
                            {
                                "name": "英国",
                                "type": "Nationality",
                                "category": "GeographicLocation",
                                "description": "大不列颠，包括英格兰、苏格兰和威尔士的岛屿。"
                            },
                            {
                                "name": "史蒂夫·巴克",
                                "type": "Director",
                                "category": "Person",
                                "description": "史蒂夫·巴克 是一名英国电影导演和剧作家"
                            },
                            {
                                "name": "保罗·格斯滕伯格",
                                "type": "Writer",
                                "category": "Person",
                                "description": "保罗·格斯滕伯格 (Paul Gerstenberger) 是一名作家和制片人，因《The Rezort》（2015 年）、《Primeval》（2007 年）和《House of Anubis》（2011 年）而闻名。"
                            },
                            {
                                "name": "道格雷·斯科特",
                                "type": "Actor",
                                "category": "Person",
                                "description": "斯蒂芬·道格雷·斯科特 (Stephen Dougray Scott，1965 年 11 月 26 日出生) 是一位苏格兰演员。"
                            },
                            {
                                "name": "杰西卡·德·古维",
                                "type": "Actor",
                                "category": "Person",
                                "description": "杰西卡·伊莉斯·德·古维 (Jessica Elise De Gouw，1988 年 2 月 15 日出生) 是一位澳大利亚女演员。"
                            },
                            {
                                "name": "马丁·麦肯",
                                "type": "Actor",
                                "category": "Person",
                                "description": "马丁·麦肯是来自北爱尔兰的演员。2020 年，他在《爱尔兰时报》爱尔兰最伟大电影演员名单中排名第 48 位"
                            }
                        ]
            }
        ],
        "input": "$input"
    }    
        """

    def __init__(self, language: str = "", **kwargs):
        super().__init__(language, **kwargs)
        project_schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
        self.schema = []
        for name, value in project_schema.items():
            # filter out index types
            if value.spg_type_enum != SpgTypeEnum.Index:
                self.schema.append(name)

        self.template = Template(self.template).safe_substitute(
            schema=json.dumps(self.schema)
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
