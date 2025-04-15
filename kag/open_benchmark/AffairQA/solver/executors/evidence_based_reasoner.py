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
import asyncio
import json
from kag.interface import ExecutorABC, LLMClient, Task, Context


@ExecutorABC.register("evidence_based_reasoner")
class EvidenceBasedReasoner(ExecutorABC):
    def __init__(self, llm: LLMClient, retriever: ExecutorABC):
        self.llm = llm
        self.retriever = retriever

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        retrieve_task = Task(
            executor=self.retriever.schema()["name"],
            arguments=task.arguments,
            id=task.id,
        )
        await asyncio.to_thread(
            lambda: self.retriever.invoke(query, retrieve_task, context)
        )
        retrieved_docs = []
        if hasattr(retrieve_task.result, "chunk_datas"):
            retrieved_docs.extend(retrieve_task.result.chunk_datas)
            retrieved_docs = "\\n\\n".join([x.content for x in retrieved_docs])
        else:
            retrieved_docs = str(retrieve_task.result)

        system_instruction = """
作为一名精通解决复杂多跳问题的专家，我需要您的协助来处理一个多跳问题。该问题已被分解为多个直接的单跳查询，其中每个问题可能依赖于先前问题的回答，即问题主体可能包含诸如 "{{i.output}}" 之类的内容，这表示第 i 个子问题的答案。我将为您提供关于如何处理这些初步问题的见解，或者提供答案本身，这些对于准确解决问题至关重要。此外，我将提供与当前问题相关的文本摘录，建议您仔细阅读并彻底理解。请以 "思考过程: " 开始您的回答，在此处您将概述得出结论的逐步思考过程。以 "答案: " 结束，提供一个清晰、准确的回答，无需任何额外评论。

文档:
西尔维斯特
西尔维斯特是一个源自拉丁语形容词 silvestris 的名字，意为“树木繁茂的”或“野生的”，该形容词源自名词 silva，意为“林地”。古典拉丁语中拼写为 i。在古典拉丁语中，y 代表一个与 i 不同的独立发音，不是拉丁语本土发音，而是用于转写外来词。古典时期之后，y 开始发音为 i。用 Sylv- 代替 Silv- 的拼写方式出现在古典时期之后。

伊利诺伊州香槟县斯坦顿镇
斯坦顿镇是美国伊利诺伊州香槟县的一个镇。根据 2010 年人口普查，其人口为 505 人，拥有 202 个住房单元。


纽约州蒙蒂贝洛
蒙蒂贝洛（意大利语：“美丽的山”）是美国纽约州罗克兰县拉马波镇的一个建制村。它位于萨芬以北，希尔本以东，韦斯利希尔斯以南，艾尔蒙特以西。根据 2010 年人口普查，人口为 4,526 人。

埃里克·霍特
埃里克·霍特（1987 年 2 月 16 日出生于纽约州蒙蒂贝洛）是一名美国足球运动员，目前是自由球员。


问题:
0: 公元 800 年谁被加冕为西罗马帝国皇帝？
思考过程: 提供的关于查理曼的段落表明他于 800 年被加冕为神圣罗马帝国皇帝。 答案: 查理曼。

1: {{0.output}} 后来以什么名字著称？
思考过程: 要确定 {{0.output}} (查理曼) 后来以什么名字著称，我需要回顾提供的关于查理曼的段落。该段落表明查理曼也被称为“查理大帝”。 答案: 查理大帝

2: 在 {{0.output}} 时代，姓氏 Sylvester 起源于哪种语言？
思考过程: 问题询问在 {{0.output}}（即查理曼，其统治时期为中世纪早期）时代姓氏 Sylvester 的起源。关于 Sylvester 这个名字的段落指出它源自拉丁语。 答案: 拉丁语
"""
        query = f"{task.id}: {task.arguments['query']}"
        subqa = []
        for pt in task.parents:
            subq = f"{pt.id}: {pt.arguments['query']}"
            result = json.loads(pt.result)
            suba = str(result["response"])
            subqa.append(f"{subq}\n{suba}")
        subqa = "\n\n".join(subqa)
        request = f"{system_instruction}\nDocs:\n{retrieved_docs}\nQuestions:\n{subqa}\n{query}"

        # print(f"Reasoner request = {request}")
        response = await self.llm.acall(request)
        response = response+ "请结合信息等其他信息获取答案！"
        # print(f"Reasoner response = {response}")
        task.update_memory("retriever", retrieve_task.result)
        task.result = json.dumps(
            {"query": task.arguments["query"], "response": response}, ensure_ascii=False
        )

        return response

    def schema(self, func_name: str = None):
        return {
            "name": "Reasoner",
            "description": "Synthesizes precise, evidence-backed answers to user queries by analyzing provided contextual documents. Note: Contextual documents are pre-loaded and processed implicitly; no explicit context parameter is required.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query.",
                    "optional": False,
                },
            },
        }
