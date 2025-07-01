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


@PromptABC.register("default_retriever_static_planning")
class RetrieverStaticPlanningPrompt(PromptABC):
    template_zh = {
        "instruction": """

你是一个问题求解规划器，你的任务是分析用户提供的复杂问题，并通过你的分析和推理，给出基于可用工具来解决该问题的具体步骤规划，以有向无环图（DAG）表示。注意你并不需要回答该问题，而是产出回答问题所需的步骤。其中用户问题在query字段给出，可用工具在executors字段中给出。
\n你的推理需遵循以下步骤：
1. 分析请求以理解任务范围
2. 将原始复杂问题拆解成若干个最细粒度的原子问题集，以及这些原子问题集的依赖关系（DAG格式）。
3. 使用executors定义的工具创建清晰、可操作的计划，推动任务取得实质性进展。
\n注意事项：
1. 请以json 格式返回你的规划结果，参考example字段中output字段的示例。
""",
        "example": {
            "query": "张学友和刘德华共同出演过哪些电影",
            "executors": [
                {
                    "name": "Retriever",
                    "description": "Retrieve relevant knowledge from the local knowledge base.",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "User-provided query for retrieval.",
                            "optional": False,
                        },
                    },
                },
            ],
            "output": {
                "0": {
                    "executor": "Retriever",
                    "dependent_task_ids": [],
                    "arguments": {"query": "张学友出演过的电影列表"},
                },
                "1": {
                    "executor": "Retriever",
                    "dependent_task_ids": [],
                    "arguments": {"query": "刘德华出演过的电影列表"},
                },
            },
        },
    }
    template_en = {
        "instruction": """

You are a problem-solving planner. Your task is to analyze complex problems provided by users and, through your analysis and reasoning, provide specific step-by-step plans for solving the problem using available tools. The plan should be represented as a Directed Acyclic Graph (DAG). Note that you do not need to answer the question directly but instead produce the steps required to answer the question. The user's question is provided in the query field, and the available tools are listed in the executors field.

Your reasoning should follow these steps:
1. Analyze the request to understand the scope of the task.
2. Break down the original complex problem into several finest-grained atomic problem sets and define their dependencies in DAG format.
3. Use the tools defined in executors to create clear and actionable plans to drive the task forward and make substantial progress.

Note:
1. Please return your planning result in JSON format, following the example in the output field of the example section.
""",
        "example": {
            "query": "Which year was Zhou Xingchi's first movie released?",
            "executors": [
                {
                    "name": "Retriever",
                    "description": "Retrieve relevant knowledge from the local knowledge base.",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "User-provided query for retrieval.",
                            "optional": False,
                        },
                    },
                },
            ],
            "output": {
                "0": {
                    "executor": "Retriever",
                    "dependent_task_ids": [],
                    "arguments": {"query": "What was Zhou Xingchi's first movie?"},
                },
                "1": {
                    "executor": "Retriever",
                    "dependent_task_ids": ["0"],
                    "arguments": {"query": "Which year was {{0.output}} released?"},
                },
            },
        },
    }

    @property
    def template_variables(self) -> List[str]:
        return ["executors", "query"]

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got {type(response)}")
        if "output" in response:
            response = response["output"]
        return Task.create_tasks_from_dag(response)
