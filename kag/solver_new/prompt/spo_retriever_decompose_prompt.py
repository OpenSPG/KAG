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


@PromptABC.register("default_spo_retriever_decompose")
class DefaultSPORetrieverDecomposePrompt(PromptABC):
    template_zh = {
        "instruction": """你是一个图谱检索器，需要生成一些多跳查询计划用于匹配图结构""",
        "format": [
            "以json格式的列表输出",
            "每一个元素中需要包含起点s、关系p、终点o、子查询sub_query",
            "s/p/o中至少包含alias信息，用于代表该模式图名"
        ],
        "example": {
            "query": "张学友和刘德华共同出演过哪些电影",
            "context": [],
            "output": [
                {
                    "sub_query": "张学友参演过哪些电影",
                    "s": {
                        "alias": "s1",
                        "name": "张学友",
                        "type": "人物",
                    },
                    "p": {
                        "alias": "p1",
                        "type": "参演",
                    },
                    "o": {
                        "alias": "o1",
                        "type": "电影",
                    }
                },
                {
                    "sub_query": "张学友参演过电影中，刘德华也参演",
                    "s": {
                        "alias": "s2",
                        "name": "刘德华",
                        "type": "人物",
                    },
                    "p": {
                        "alias": "p2",
                        "type": "参演",
                    },
                    "o": {
                        "alias": "o1"
                    }
                }
            ],
        },
        "input": {
            "query": "$query",
            "context": "$context",
       },
    }
    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return ["context", "query"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got {type(response)}")
        if "output" in response:
            response = response["output"]
        if not isinstance(response, list):
            raise ValueError(f"spo retriever code should be a list, but got {type(response)}")
        for res in response:
            assert (
                    isinstance(res, dict)
                    and "s" in res and "alias" in res["s"]
                    and "p" in res and "alias" in res["p"]
                    and "o" in res and "alias" in res["o"]
            ), "ele must be a dict with `alias` and `s\p\o` "
        return response
