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

from kag.interface import GeneratorABC, LLMClient


@GeneratorABC.register("kag_prqa_generator")
class PrqaGenerator(GeneratorABC):
    def __init__(self, llm: LLMClient, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    def invoke(self, query, context, **kwargs):
        raw_data = kwargs.get("raw_data")
        return self.post_process(raw_data, query)

    def post_process(self, raw_data: List, question: str) -> str:
        """后处理生成自然语言回答"""
        if not raw_data:
            return "未找到相关信息"

        prompt = self.build_analysis_prompt(raw_data, question)
        return self.llm(prompt)

    def build_analysis_prompt(self, data: List, question: str) -> str:
        """构建分析提示词"""
        prompt_lines = [
            "从以下路径关系中分析问题：",
            *self.format_analysis_data(data),
            f"\n分析问题：“{question}”的答案",
            "请按照以下步骤完成：",
            "1. **提取逻辑链条**：逐步分析路径数据中与问题相关的关键信息",
            "2. **确定问题目标**：明确问题需要获取的核心信息",
            "3. **组织答案**：用简洁自然的中文回答，包含必要细节(如果有多个答案，请全部回答出来)",
            "只用最精简的结果给出答案，不要分析步骤的内容，多个答案时用顿号'、'隔开，除此之外不要有冗余字符; 如果分析后没有问题的对应答案，直接回答'未找到相关信息‘",
        ]
        return "\n".join(prompt_lines)

    @staticmethod
    def format_analysis_data(data: List) -> List[str]:
        """格式化分析数据"""
        formatted = []
        for item in data:
            if isinstance(item, str):
                formatted.append(item)
            elif isinstance(item, dict):
                formatted.append(json.dumps(item, ensure_ascii=False))
        return formatted
