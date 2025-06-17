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
from knext.reasoner.client import ReasonerClient


@PromptABC.register("default_mcp_tool_call")
class MCPToolCallPrompt(PromptABC):

    template_zh = """在这个环境中，你可以使用一系列工具来回答用户的问题。
                    你可以通过编写形如以下的 <tool_calls> 块来调用函数：
                    <tool_calls>
                    <tool_call id="call_1">
                    <tool_name>tool_name</tool_name>
                    <parameters>
                    {"param1": "value1", "param2": "value2"}
                    </parameters>
                    </tool_call>
                    </tool_calls>
                    
                    以下是可用的工具：
                    {
                      "tools": [
                        {
                          "name": "search_web",
                          "description": "搜索互联网获取信息",
                          "parameters": {
                            "query": "搜索查询内容"
                          }
                        },
                        {
                          "name": "get_weather",
                          "description": "获取特定地点的天气信息",
                          "parameters": {
                            "location": "地点名称",
                            "unit": "温度单位 (celsius 或 fahrenheit)"
                          }
                        }
                      ]
                    }
                    
                    使用工具时，请遵循以下步骤：
                    1. 分析用户查询，确定需要使用的工具
                    2. 使用上述格式调用适当的工具
                    3. 等待工具返回结果
                    4. 基于工具结果回答用户的问题 
                    如果工具返回结果不足以回答用户问题，你可以进行多次工具调用。
                    如果不需要使用任何工具就能回答用户问题，直接回答即可，无需进行工具调用。"""
    template_en = template_zh

    def build_prompt(self, query: str):
        messages = [
            {"role": "system", "content": self.template},
            {"role": "user", "content": query},
        ]
        return messages
