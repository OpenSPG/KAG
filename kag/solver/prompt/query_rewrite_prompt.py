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
from kag.interface import PromptABC


@PromptABC.register("default_query_rewrite")
class QueryRewritePrompt(PromptABC):
    template_zh = {
        "instruction": """
你是一个具备语义聚焦能力的问题重构引擎，需要将query字段中包含{{N.output}}占位符的问题转化为可独立处理的完整问题。当前核心挑战是从非结构化的长答案中提取精准匹配的语义片段。
\n1. 输入规范
- input字段是一个dict，包含了当前待改写的问题，包含{{N.output}}占位符的原始问题（N为父节点ID）
- context表示父节点上下文
\n2. 处理流程
- 占位符解析：识别所有{{数字.output}}模式，记录需处理的parent_id集合
- 上下文检索：对每个parent_id：
  a. 定位对应父节点的question-answer对
  b. 建立问题焦点：将父question作为信息提取的语义锚点
- 信息蒸馏：
   a. 解析父question的答案类型（如人名/地点/日期）
   b. 从answer中提取最匹配问题类型的核心片段
   c. 验证提取结果是否可直接代入当前问题语境
- 问题改写：
  a. 将父节点答案带入待改写问题，并进行润色，确保改写后的问题准确、通畅且与原问题意图一致。
  b. 改写后的问题需要与input字段格式一致，即具有相同的dict格式以及相同的key。
  c. 注意要保持问题的语种。
\nexample字段中给出了一个简单的示例供参考。请直接返回改写后的问题字符串，正如example的output字段一样。
        """,
        "example": {
            "input": {"query": "{{0.output}}获得的奖项中，有哪些是{{1.output}}没有获得过的"},
            "context": {
                "0": {
                    "output": [
                        "六小龄童出生于1959年，祖籍浙江绍兴，是国家一级演员，曾担任浙江大学人文学院兼职教授。他在1982年《西游记》拍摄期间全程担任孙悟空的主演，凭借该角色获得中国第六届“金鹰奖”最佳男主角奖‌"
                    ],
                },
                "1": {
                    "output": [
                        "歌曲《青花瓷》由方文山作词，周杰伦作曲，钟兴民编曲，收录在周杰伦于2007年11月2日发行的个人第八张音乐专辑《我很忙》中‌"
                    ],
                },
            },
            "output": {"query": "在六小龄童获得的奖项中，有哪些是周杰伦没有获得过的？"},
        },
    }

    template_en = {
        "instruction": """You are an expert skilled in restructuring multi-step queries. The original multi-step query has been broken down into several straightforward single-step query, each of which may explicitly (in the form of "{{i.output}}") or implicitly (such as "the person," "the city") rely on the answers to preceding queries. Please replace the references to the answers of previous queries in the provided query with the actual answers, based on the thought by the preceding queries, and rephrase the question accordingly. Refer to the example for the output format.

        
\nThe example field provides a simple example for reference. Please return only the reformulated question string IN JSON FORMAT, follow the format of  output field in the example.
        """,
        "example": {
            "input": {
                "query": "{{0.output}} has won awards, which ones have not been obtained by {{1.output}}?"
            },
            "context": {
                "0": {
                    "query": "Who played Sun Wukong in Journey to the West?",
                    "output": [
                        "Liu Xiao Ling Tong was born in 1959 and hails from Shaoxing, Zhejiang. He is a National Class-A Actor and has served as an adjunct professor at the School of Humanities, Zhejiang University. During the filming of the TV series 'Journey to the West' in 1982, he played the role of Sun Wukong throughout, winning the Best Actor Award at the 6th China Golden Eagle Awards for his performance. Answer: Liu Xiao Ling Tong"
                    ],
                },
                "1": {
                    "query": "Who sing the song 'Blue and White Porcelain'?",
                    "output": [
                        "The song 'Blue and White Porcelain' was written by Vincent Fang, composed by Jay Chou, arranged by Roger Chung, and included in Jay Chou’s eighth studio album 'I'm Busy', released on November 2, 2007. Answer: JayChou"
                    ],
                },
            },
            "output": {
                "query": "Among the awards won by Liu Xiao Ling Tong, which ones have not been won by Jay Chou?"
            },
        },
    }

    @property
    def template_variables(self) -> List[str]:
        return ["context", "query"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict) and "output" in response:
            response = response["output"]

        if not isinstance(response, dict):
            raise ValueError(
                f"response should be a dict, but got {type(response)}: {response}"
            )
        return response
