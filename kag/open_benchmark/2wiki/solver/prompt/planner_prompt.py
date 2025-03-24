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

    @property
    def template_variables(self) -> List[str]:
        return ["executors", "query"]

    def format_dag(self, response: Dict):
        def get_retrieve_task_id(task_id):
            return str(int(task_id) * 2)

        def get_reason_task_id(task_id):
            return str(int(task_id) * 2 + 1)

        def update_task_id(query):
            parts = re.split(r"(\{\{.*?\}\})", query)
            new_query = []
            for part in parts:
                if re.match("(\{\{.*?\}\})", part):
                    task_id = part.lstrip("{{").rstrip(".output}}")
                    new_task_id = get_reason_task_id(task_id)
                    new_query.append("{{" + new_task_id + ".output}}")
                else:
                    new_query.append(part)
            return "".join(new_query)

        new_tasks = {}
        for task_id, task_info in response.items():
            retrieve_task_id = get_retrieve_task_id(task_id)
            dependent_task_ids = [
                get_reason_task_id(x) for x in task_info["dependent_task_ids"]
            ]
            retrieve_task = {
                "executor": "Retriever",
                "dependent_task_ids": dependent_task_ids,
                "arguments": {"query": update_task_id(task_info["query"])},
            }
            reason_task_id = get_reason_task_id(task_id)
            reason_task = {
                "executor": "Reasoner",
                "dependent_task_ids": dependent_task_ids + [retrieve_task_id],
                "arguments": {"query": update_task_id(task_info["query"])},
            }
            new_tasks[retrieve_task_id] = retrieve_task
            new_tasks[reason_task_id] = reason_task

        print(f"Planning output:\n{new_tasks}")
        return new_tasks

    def parse_response(self, response: str, **kwargs):
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict):
            raise ValueError(f"response should be a dict, but got {type(response)}")
        if "output" in response:
            response = response["output"]
        return Task.create_tasks_from_dag(self.format_dag(response))


# @PromptABC.register("retriever_static_planning")
# class StaticPlanningPrompt(PromptABC):
#     template_zh = {
#         "instruction": """

# 你是一个问题求解规划器，你的任务是分析用户提供的复杂问题，并通过你的分析和推理，给出基于可用工具来解决该问题的具体步骤规划，以有向无环图（DAG）表示。注意你并不需要回答该问题，而是产出回答问题所需的步骤。其中用户问题在query字段给出，可用工具在executors字段中给出。
# \n你的推理需遵循以下步骤：
# 1. 分析请求以理解任务范围
# 2. 将原始复杂问题拆解成若干个最细粒度的原子问题集，以及这些原子问题集的依赖关系（DAG格式）。
# 3. 使用executors定义的工具创建清晰、可操作的计划，推动任务取得实质性进展。
# \n注意事项：
# 1. 请以json 格式返回你的规划结果，参考example字段中output字段的示例。
# """,
#         "example": {
#             "query": "张学友和刘德华共同出演过哪些电影",
#             "executors": [
#                 {
#                     "name": "Retriever",
#                     "description": "Retrieve relevant knowledge from the local knowledge base.",
#                     "parameters": {
#                         "query": {
#                             "type": "string",
#                             "description": "User-provided query for retrieval.",
#                             "optional": False,
#                         },
#                     },
#                 },
#                 {
#                     "name": "Reasoner",
#                     "description": "Generate answers to user query based on the context.",
#                     "parameters": {
#                         "query": {
#                             "type": "string",
#                             "description": "User-provided query for retrieval.",
#                             "optional": False,
#                         },
#                     },
#                 },
#             ],
#             "output": {
#                 "0": {
#                     "executor": "Retriever",
#                     "dependent_task_ids": [],
#                     "arguments": {"query": "张学友出演过的电影列表"},
#                 },
#                 "1": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["0"],
#                     "arguments": {"query": "张学友出演过的电影列表"},
#                 },
#                 "2": {
#                     "executor": "Retriever",
#                     "dependent_task_ids": [],
#                     "arguments": {"query": "刘德华出演过的电影列表"},
#                 },
#                 "3": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["2"],
#                     "arguments": {"query": "张学友出演过的电影列表"},
#                 },
#                 "4": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["1", "3"],
#                     "arguments": {
#                         "query": "张学友出演的电影有{{1.output}}, 刘德华出演的电影有{{3.output}},请问他们共同出演的电影有哪些。"
#                     },
#                 },
#             },
#         },
#     }
#     template_en = {
#         "instruction": """

# You are a problem-solving planner. Your task is to analyze complex problems provided by users and, through your analysis and reasoning, provide specific step-by-step plans for solving the problem using available tools. The plan should be represented as a Directed Acyclic Graph (DAG). Note that you do not need to answer the question directly but instead produce the steps required to answer the question. The user's question is provided in the query field, and the available tools are listed in the executors field.

# Your reasoning should follow these steps:
# 1. Analyze the complex multi-hop problem to understand the scope of the task.
# 2. Break down the original complex multi-hop problem into several SINGLE-HOP problem sets and define their dependencies in DAG format.
# 3. Use the tools defined in executors to create clear and actionable plans to drive the task forward and make substantial progress.

# Note:
# 1. Please return your planning result in JSON format, following the example in the output field of the example section.
# 2.
# """,
#         "example": {
#             "query": "Which movies have been starred by both Jacky Cheung and Andy Lau?",
#             "executors": [
#                 {
#                     "name": "Retriever",
#                     "description": "Retrieve relevant documents that may be helpful in answering the user query. Note: it can only retrieve relevant documents and cannot generate the answer to the question. ",
#                     "parameters": {
#                         "query": {
#                             "type": "string",
#                             "description": "User-provided query for retrieval.",
#                             "optional": False,
#                         },
#                     },
#                 },
#                 {
#                     "name": "Reasoner",
#                     "description": "Generate concise and accurate answers to user questions based on the context of the search results. Note: The context will be passed implicitly, so there is no need to include context information in the arguments.",
#                     "parameters": {
#                         "query": {
#                             "type": "string",
#                             "description": "User-provided query.",
#                             "optional": False,
#                         },
#                     },
#                 },
#             ],
#             "output": {
#                 "0": {
#                     "executor": "Retriever",
#                     "dependent_task_ids": [],
#                     "arguments": {
#                         "query": "Which movies have been starred by Jacky Cheung?"
#                     },
#                 },
#                 "1": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["0"],
#                     "arguments": {
#                         "query": "Generate the list of movies starred by Jacky Cheung",
#                     },
#                 },
#                 "2": {
#                     "executor": "Retriever",
#                     "dependent_task_ids": [],
#                     "arguments": {
#                         "query": "Which movies have been starred by Andy Lau?"
#                     },
#                 },
#                 "3": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["2"],
#                     "arguments": {
#                         "query": "Generate the list of movies starred by Andy Lau",
#                     },
#                 },
#                 "4": {
#                     "executor": "Reasoner",
#                     "dependent_task_ids": ["1", "3"],
#                     "arguments": {
#                         "query": "The movies starred by Jacky Cheung are {{1.output}}, and the movies starred by Andy Lau are {{3.output}}. Which movies have they starred in together?"
#                     },
#                 },
#             },
#         },
#     }

#     @property
#     def template_variables(self) -> List[str]:
#         return ["executors", "query"]

#     def parse_response(self, response: str, **kwargs):
#         if isinstance(response, str):
#             response = json.loads(response)
#         if not isinstance(response, dict):
#             raise ValueError(f"response should be a dict, but got {type(response)}")
#         if "output" in response:
#             response = response["output"]
#         print(f"Planning output:\n{response}")
#         return Task.create_tasks_from_dag(response)
