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
from kag.interface import PromptABC, Task


@PromptABC.register("default_iterative_planning")
class DefaultIterativePlanningPrompt(PromptABC):
    template_zh = {
        "instruction": """
你是一个问题求解规划器，你的任务是分析用户提供的复杂问题以及问题求解上下文（包含了历史步骤规划和执行结果），基于你自身的推理，**逐步地**规划出基于可用工具来解决该问题的具体步骤。其中用户问题在query字段给出，可用工具在executors字段中给出，问题求解上下文在context字段中给出，包括执行的工具调用与调用结果。
\n你的推理需遵循以下步骤：
1. 分析请求以理解任务范围
2. 阅读分析上下文，了解问题求解进度，判断下一步需要执行的动作。如果上下文为空，表明需要从头考虑
3. 使用executors定义的工具创建清晰、可操作的计划，推动任务取得实质性进展
\n注意事项：
1. 请以json 格式返回你的规划结果，参考example字段中output字段的示例。
2. 如果你从context中判断任务已经结束，请返回Finish工具调用，表示无需再执行任何操作。
""",
        "example": {
            "query": "张学友和刘德华共同出演过哪些电影",
            "context": [],
            "executors": [
                {
                    "name": "Retriever",
                    "description": "Retrieve relevant knowledge from the local knowledge base.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "User-provided query for retrieval.",
                            },
                        },
                    },
                },
                {
                    "name": "Math",
                    "description": "Peform Math computation based on use query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "User-provided query for retrieval.",
                            },
                        },
                    },
                },
                {
                    "name": "Finish",
                    "description": "Performs no operation and is solely used to indicate that the task has been completed.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            ],
            "output": {
                "executor": {
                    "name": "Retriever",
                    "arguments": {"query": "张学友出演的电影列表"},
                }
            },
        },
    }

    @property
    def template_variables(self) -> List[str]:
        return ["context", "executors", "query"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got {type(response)}")
        if "output" in response:
            response = response["output"]
        assert (
            isinstance(response, dict) and "executor" in response
        ), "repsonse must be a dict with `executor`"
        executor = response["executor"]
        assert (
            isinstance(executor, dict)
            and "name" in executor
            and "arguments" in executor
        ), "repsonse must be a dict with `name` and `arguments`"
        task = Task(executor=executor["name"], arguments=executor["arguments"])
        return [task]
