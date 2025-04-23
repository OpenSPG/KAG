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
import re
from typing import List, Dict
from kag.interface import PromptABC, Task


@PromptABC.register("retriever_static_planning")
class StaticPlanningPrompt(PromptABC):
    template_en = {
        "instruction": """
The `query` field contains a complex multi-hop question that can be broken down into a series of simple single-hop questions. Your task is to carefully analyze the logical structure of the question, then decompose the multi-hop question into a series of single-hop atomic questions, and provide the dependencies between these sub-questions. The dependencies should be represented as a Directed Acyclic Graph (DAG).
  
Decompose the original multi-hop question into a series of single-hop atomic questions and carefully analyze their dependencies, representing them in the form of a DAG. If Question 2 depends on Question 1, then the answer to Question 1 must be explicitly referenced within Question 2.
  
Please complete the task according to the following rules:
1. Atomic Decomposition:
   - Break down the multi-hop question in the `query` field into the finest-grained single-hop sub-questions.
   - Each sub-question must be independently executable; implicit multi-hop operations are strictly prohibited (e.g., "the birthday of X's director" must be split into two sub-questions: "X's director" and "[Director]'s birthday").
        
2. Dependency Modeling:
   - Use a DAG to clearly define the dependencies between sub-questions.
   - Downstream tasks must explicitly reference upstream results using `{{i.output}}` (e.g., if Question 2 depends on Question 1, the query for Question 2 must include `{{1.output}}`).
        
3. Output Specification:
   - The `example` field provides a sample query and the expected output (in the `output` field). Strictly follow the output format and provide your response in JSON format.        
""",
        "example": {
            "query": "Which movies have been starred by both Jacky Cheung and Andy Lau?",
            "output": {
                "0": {
                    "dependent_task_ids": [],
                    "query": "Which movies have been starred by Jacky Cheung?",
                },
                "1": {
                    "dependent_task_ids": [],
                    "query": "Which movies have been starred by Andy Lau?",
                },
                "2": {
                    "dependent_task_ids": ["0", "1"],
                    "query": "The movies starred by Jacky Cheung are {{0.output}}, and the movies starred by Andy Lau are {{1.output}}. Which movies have they starred in together?",
                },
            },
        },
    }

    template_zh = {
        "instruction": """
`query` 字段包含一个复杂的多跳问题，可以拆分为一系列简单的单跳问题。您的任务是仔细分析问题的逻辑结构，将多跳问题分解为一系列单跳原子问题，并提供这些子问题之间的依赖关系。依赖关系应表示为有向无环图(DAG)。
  
将原始多跳问题分解为一系列单跳原子问题，并仔细分析它们的依赖关系，以DAG的形式表示。如果问题2依赖于问题1，那么问题1的答案必须在问题2中明确引用。
  
请按照以下规则完成任务：
1. 原子分解：
   - 将`query`字段中的多跳问题分解为最细粒度的单跳子问题。
   - 每个子问题必须能够独立执行；严格禁止隐式多跳操作（例如，"X导演的生日"必须分为两个子问题："X的导演"和"[导演]的生日"）。
        
2. 依赖关系建模：
   - 使用DAG清晰定义子问题之间的依赖关系。
   - 下游任务必须使用`{{i.output}}`明确引用上游结果（例如，如果问题2依赖于问题1，则问题2的查询必须包含`{{1.output}}`）。
        
3. 输出规范：
   - `example`字段提供了一个示例查询和预期输出（在`output`字段中）。严格遵循输出格式，并以JSON格式提供您的响应。        
""",
        "example": {
            "query": "张学友和刘德华都出演过哪些电影？",
            "output": {
                "0": {
                    "dependent_task_ids": [],
                    "query": "张学友出演过哪些电影？",
                },
                "1": {
                    "dependent_task_ids": [],
                    "query": "刘德华出演过哪些电影？",
                },
                "2": {
                    "dependent_task_ids": ["0", "1"],
                    "query": "张学友出演的电影有{{0.output}}，刘德华出演的电影有{{1.output}}。他们共同出演过哪些电影？",
                },
            },
        },
    }

    @property
    def template_variables(self) -> List[str]:
        return ["executors", "query"]

    def format_dag(self, response: Dict):
        tasks = {}
        for task_id, task_info in response.items():
            reason_task = {
                "executor": "Reasoner",
                "dependent_task_ids": task_info["dependent_task_ids"],
                "arguments": {"query": task_info["query"]},
            }
            tasks[task_id] = reason_task
        return tasks

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got {type(response)}")
        if "output" in response:
            response = response["output"]
        return Task.create_tasks_from_dag(self.format_dag(response))
