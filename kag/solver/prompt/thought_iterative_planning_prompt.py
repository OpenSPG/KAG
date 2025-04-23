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
import logging
import json
from typing import List
from kag.interface import PromptABC, Task

logger = logging.getLogger()


@PromptABC.register("default_thought_iterative_planning")
class DefaultIterativePlanningPrompt(PromptABC):
    example_executors = [
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
        {
            "name": "Math",
            "description": "Used to address users' math or computational problems.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The computable problem derived from the user's input question, retaining the essential information for the calculation target and dependencies.",
                    "optional": False,
                }
            },
        },
        {
            "name": "Deduce",
            "description": "Synthesizes precise, evidence-backed answers to user queries by analyzing provided contextual documents. Note: Contextual documents are pre-loaded and processed implicitly; no explicit context parameter is required.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query.",
                    "optional": False,
                },
            },
        },
        {
            "name": "Finish",
            "description": "Performs no operation and is solely used to indicate that the task has been completed.",
            "parameters": {},
        },
    ]
    template_zh = {
        "instruction": "你是一个问题解决规划者。你的任务是分析用户提供的复杂问题及问题解决上下文（包括历史规划步骤和执行结果）。通过自主推理，你需要**分步骤**规划使用可用工具的具体行动以解决问题。用户的问题保存在“query”字段，可用工具列在“executors”字段，而包含已执行工具调用及结果的问题解决上下文则存储在“context”字段中。你的推理需遵循以下步骤：\n\n1. 解析请求以理解任务范围\n2. 阅读并分析上下文，理解问题解决进展并确定下一步行动。若上下文为空，则从零开始制定计划\n3. 使用“executors”字段定义的工具创建清晰可执行的计划，推动任务实质性进展\n\n重要注意事项：\n1. 请以JSON格式返回规划结果，格式需符合示例的“output”字段\n2. 若通过上下文判断任务已完成后，返回“Finish”工具调用表示无需进一步操作",
        "example1": {
            "query": "爱因斯坦获得诺贝尔奖时多少岁？",
            "context": [],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Retriever",
                    "arguments": {"query": "爱因斯坦出生于哪一年？"},
                    "thought": "首要需求：要计算获奖时年龄，必须首先获取出生年份。这是后续计算的基础数据",
                }
            },
        },
        "example2": {
            "query": "爱因斯坦获得诺贝尔奖时多少岁？",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "爱因斯坦出生于哪一年？"},
                    "result": "1879",
                }
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Retriever",
                    "arguments": {"query": "爱因斯坦哪一年获得诺贝尔奖？"},
                    "thought": "已确认出生年份：1879。接下要求解的关键数据：诺贝尔奖年份。年龄计算需要两个时间基准点",
                }
            },
        },
        "example3": {
            "query": "爱因斯坦获得诺贝尔奖时多少岁？",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "爱因斯坦出生于哪一年？"},
                    "result": "1879",
                },
                {
                    "executor": "Retriever",
                    "arguments": {"query": "爱因斯坦哪一年获得诺贝尔奖？"},
                    "result": "1921",
                },
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Math",
                    "arguments": {"query": "用1921减去1879计算年龄"},
                    "thought": "核心数据已获取：出生年份（1879）和获奖年份（1921）。执行公式：获奖年份-出生年份=年龄。需要数学验证",
                }
            },
        },
        "example4": {
            "query": "爱因斯坦获得诺贝尔奖时多少岁？",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "爱因斯坦出生于哪一年？"},
                    "result": "1879",
                },
                {
                    "executor": "Retriever",
                    "arguments": {"query": "爱因斯坦哪一年获得诺贝尔奖？"},
                    "result": "1921",
                },
                {
                    "executor": "Math",
                    "arguments": {"query": "用1921减去1879计算年龄"},
                    "result": "42",
                },
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Deduce",
                    "arguments": {"query": "结合出生年份和获奖年份确定年龄"},
                    "thought": "计算结果为42岁。需要验证：1.是否符合历史记录 2.是否存在时间线异常（如获奖延迟）。需综合上下文信息最终确认",
                }
            },
        },
    }

    template_en = {
        "instruction": """
You are a problem-solving planner. Your task is to analyze the complex problem provided by the user along with the problem-solving context (including historical planning steps and execution results). Based on your own reasoning, you should **step-by-step** plan specific actions to solve the problem using the available tools. The user's problem is provided in the "query" field, the available tools are listed in the "executors" field, and the problem-solving context, which includes executed tool calls and their results, is given in the "context" field.

Your reasoning should follow these steps:
1. Analyze the request to understand the scope of the task.
2. Read and analyze the context to understand the progress made in problem-solving and determine the next actions to execute. If the context is empty, start planning from scratch.
3. Use the tools defined in the "executors" field to create a clear, actionable plan that drives substantive progress on the task.

Important considerations:
1. Return your planning results in JSON format, following the example provided in the "output" field of the "example" section.
2. If you determine from the context that the task has been completed, return a "Finish" tool call to indicate no further actions are required.  
""",
        "example1": {
            "query": "How old was Albert Einstein when he won the Nobel Prize?",
            "context": [],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Retriever",
                    "arguments": {"query": "When was Albert Einstein born?"},
                    "thought": "Initial requirement: To calculate Einstein's age at the time of the award, we must first obtain his birth year. This foundational data is critical for all subsequent calculations.",
                }
            },
        },
        "example2": {
            "query": "How old was Albert Einstein when he won the Nobel Prize?",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "When was Albert Einstein born?"},
                    "result": "1879",
                }
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Retriever",
                    "arguments": {
                        "query": "What year did Albert Einstein win the Nobel Prize?"
                    },
                    "thought": "Confirmed birth year: 1879. Next critical data point: Nobel Prize year. Age calculation requires both temporal markers. Priority: Retrieve award year.",
                }
            },
        },
        "example3": {
            "query": "How old was Albert Einstein when he won the Nobel Prize?",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "When was Albert Einstein born?"},
                    "result": "1879",
                },
                {
                    "executor": "Retriever",
                    "arguments": {
                        "query": "What year did Albert Einstein win the Nobel Prize?"
                    },
                    "result": "1921",
                },
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Math",
                    "arguments": {"query": "Subtract 1879 from 1921 to get his age"},
                    "thought": "Essential data acquired: Birth year (1879) and award year (1921). Execution formula: Award year - Birth year = Age. Mathematical verification required.",
                }
            },
        },
        "example4": {
            "query": "How old was Albert Einstein when he won the Nobel Prize?",
            "context": [
                {
                    "executor": "Retriever",
                    "arguments": {"query": "When was Albert Einstein born?"},
                    "result": "1879",
                },
                {
                    "executor": "Retriever",
                    "arguments": {
                        "query": "What year did Albert Einstein win the Nobel Prize?"
                    },
                    "result": "1921",
                },
                {
                    "executor": "Math",
                    "arguments": {"query": "Subtract 1879 from 1921 to get his age"},
                    "result": "42",
                },
            ],
            "executors": example_executors,
            "output": {
                "executor": {
                    "name": "Deduce",
                    "arguments": {
                        "query": "Combine birth year and award year to confirm his age"
                    },
                    "thought": "Calculation result: 42 years old. Validation checklist: 1. Consistency with historical records 2. Potential timeline anomalies (e.g., award delays). Context synthesis needed for final confirmation.",
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
        task = Task(
            executor=executor["name"],
            arguments=executor["arguments"],
            thought=executor.get("thought", ""),
        )
        logging.info(f'{executor["arguments"]} thought {executor.get("thought", "")}')
        return [task]
