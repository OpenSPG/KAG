#
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
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("analyze_table")
class AnalyzeTablePrompt(PromptABC):
    template_zh: str = """你是一个分析表格的专家, 从table中提取信息并分析，最后返回表格有效信息"""
    template_en: str = """You are an expert in knowledge graph extraction. Based on the schema defined by the constraint, extract all entities and their attributes from the input. Return NAN for attributes not explicitly mentioned in the input. Output the results in standard JSON format, as a list."""

    def build_prompt(self, variables) -> str:
        return json.dumps(
            {
                "instruction": self.template,
                "table": variables.get("table", ""),
            },
            ensure_ascii=False,
        )

    def parse_response(self, response: str, **kwargs):
        return response
