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
from typing import List
from kag.interface import (
    ExecutorABC,
    LLMClient,
    Task,
    Context,
    RetrieverOutputMerger,
    RetrieverABC,
)


@ExecutorABC.register("evidence_based_reasoner")
class EvidenceBasedReasoner(ExecutorABC):
    def __init__(
        self,
        llm: LLMClient,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
    ):
        self.llm = llm
        self.retrievers = retrievers
        self.merger = merger

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        # retrieve_task = Task(
        #     executor=self.retriever.schema()["name"],
        #     arguments=task.arguments,
        #     id=task.id,
        # )

        retrieval_futures = []
        for retriever in self.retrievers:
            retrieval_futures.append(
                asyncio.create_task(retriever.ainvoke(task, **kwargs))
            )
        outputs = await asyncio.gather(*retrieval_futures)
        merged = await self.merger.ainvoke(task, outputs, **kwargs)

        retrieved_docs = []
        for chunk in merged.chunks:
            retrieved_docs.append(chunk.content)
        retrieved_docs = "\n\n".join(retrieved_docs)

        system_instruction = """
作为解决复杂多跳问题的专家，我需要您协助我解答一个多跳问题。该问题被拆分成多个简单的单跳查询，每个问题可能依赖于前面问题的答案，也就是说，问题正文可能包含诸如“{{i.output}}”之类的内容，表示第i个子问题的答案。我将为您提供一些关于如何解答这些初步问题（或答案本身）的见解，这些见解对于准确解决问题至关重要。此外，我将提供与当前问题相关的文本摘录，建议您仔细阅读并彻底理解。您的回复请以“思考：”开头，概述逐步得出结论的思考过程。最后以“答案：”结尾，以便清晰准确地给出答案，无需任何额外的注释。

召回文档：
Sylvester
Sylvester 这个名字源自拉丁语形容词 silvestris，意为“树木繁茂的”或“荒野的”，而 silvestris 又源自名词 silva，意为“林地”。古典拉丁语将其拼写为 i。在古典拉丁语中，y 代表与 i​​ 不同的独立发音，这并非拉丁语的固有发音，而是用于转录外来词的发音。古典时期之后，y 的发音开始为 i。用 Sylv（代替 Silv）拼写的拼写可以追溯到古典时期之后。

伊利诺伊州香槟县斯坦顿镇
斯坦顿镇是美国伊利诺伊州香槟县的一个镇区。根据 2010 年人口普查，其人口为 505 人，共有 202 个住房单元。

纽约州蒙特贝罗
蒙特贝罗（意大利语：美丽的山峰）是美国纽约州罗克兰县拉马波镇的一个建制村。它位于萨弗恩以北、希尔伯恩以东、韦斯利山以南、艾尔蒙特以西。2010 年人口普查时，人口为 4,526 人。

埃里克·霍特
埃里克·霍特（1987 年 2 月 16 日出生于纽约州蒙特贝罗）是一名美国足球运动员，目前是自由球员。

问题：
0：公元 800 年，谁被加冕为西方皇帝？
思考：提供的关于查理曼大帝的一段文字表明，他于 800 年被加冕为神圣罗马帝国皇帝。答案：查理曼大帝。

1：{{0.output}} 后来被称为什么？
思考：为了确定 {{0.oputput}}（查理曼大帝）后来被称为什么，我需要复习一下提供的关于查理曼大帝的文章。文章表明查理曼大帝也被称为“查理大帝”。答案：查理大帝

2：在 {{0.output}} 时代，Sylvester 这个姓氏起源于什么语言？
思考：这个问题询问的是 {{0.output}} 查理曼大帝统治时期，Sylvester 这个姓氏的起源，当时正值中世纪早期。关于 Sylvester 这个名字的文章指出，它源于拉丁语。答案：拉丁语
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
        # print(f"Reasoner response = {response}")
        task.update_memory("retriever", merged)
        task.result = json.dumps(
            {"query": task.arguments["query"], "response": response}, ensure_ascii=False
        )

        return response

    def schema(self, func_name: str = None):
        return {
            "name": "Retriever",
            "description": "Synthesizes precise, evidence-backed answers to user queries by analyzing provided contextual documents. Note: Contextual documents are pre-loaded and processed implicitly; no explicit context parameter is required.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query.",
                    "optional": False,
                },
            },
        }
