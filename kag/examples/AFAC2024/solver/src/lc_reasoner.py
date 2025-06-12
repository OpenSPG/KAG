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
from typing import List, Optional
from kag.interface import (
    ExecutorABC,
    LLMClient,
    Task,
    Context,
    VectorizeModelABC,
    PromptABC,
    RetrieverABC,
    RetrieverOutputMerger,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from kag.interface.solver.reporter_abc import ReporterABC


@ExecutorABC.register("long_context_reasoner")
class LongContextBasedReasoner(ExecutorABC):
    def __init__(
        self,
        llm: LLMClient,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
        vectorize_model: VectorizeModelABC,
        context_select_prompt: PromptABC,
        context_select_llm: LLMClient,
        language: str = "zh",
    ):
        self.llm = llm
        self.retrievers = retrievers
        self.merger = merger
        self.vectorize_model = vectorize_model

        self.context_select_prompt = context_select_prompt
        self.context_select_llm = context_select_llm
        self.language = language

    def rrf_merge(self, ppr_chunks: List, dpr_chunks: List):
        merged = {}
        for idx, chunk in enumerate(ppr_chunks):
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk["id"]][0]
                score += 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        for idx, chunk in enumerate(dpr_chunks):
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = 1 / (idx + 1)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        sorted_chunks = sorted(merged.values(), key=lambda x: -x[0])
        return sorted_chunks

    def weightd_merge(self, ppr_chunks: List, dpr_chunks: List, alpha: float = 0.5):
        def min_max_normalize(chunks):
            if len(chunks) == 0:
                return []
            scores = []
            for chunk in chunks:
                score = chunk["score"]
                scores.append(score)
            max_score = max(scores)
            min_score = min(scores)
            for chunk in chunks:
                score = chunk["score"]
                score = (score - min_score) / (max_score - min_score)
                chunk["score"] = score

        min_max_normalize(ppr_chunks)
        min_max_normalize(dpr_chunks)

        ppr_scores = [x["score"] for x in ppr_chunks]
        dpr_scores = [x["score"] for x in dpr_chunks]
        merged = {}
        for chunk in ppr_chunks:
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += chunk["score"] * alpha
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = chunk["score"] * alpha
                merged[chunk_attr["id"]] = (score, chunk_attr)

        for chunk in dpr_chunks:
            chunk_attr = chunk["node"]
            if chunk_attr["id"] in merged:
                score = merged[chunk_attr["id"]][0]
                score += chunk["score"] * (1 - alpha)
                merged[chunk_attr["id"]] = (score, chunk_attr)
            else:
                score = chunk["score"] * (1 - alpha)
                merged[chunk_attr["id"]] = (score, chunk_attr)

        sorted_chunks = sorted(merged.values(), key=lambda x: -x[0])
        return sorted_chunks

    async def batch_retrieve(self, task: Task, **kwargs):
        retrieval_futures = []
        for retriever in self.retrievers:
            retrieval_futures.append(
                asyncio.create_task(retriever.ainvoke(task, **kwargs))
            )
        outputs = await asyncio.gather(*retrieval_futures)
        merged = await self.merger.ainvoke(task, outputs, **kwargs)

        return merged

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def context_select(self, query: str, sorted_chunks):
        chunks = []
        for idx, item in enumerate(sorted_chunks):
            chunks.append({"idx": idx, "content": item.content})
        variables = {"question": query, "context": chunks}
        response = await self.context_select_llm.ainvoke(
            variables, self.context_select_prompt
        )
        selected_context = response["context"]
        answer = response["answer"]
        indices = []
        if len(selected_context) > 0:
            indices.extend(selected_context)
        for i in range(min(4, len(sorted_chunks))):
            if i not in indices:
                indices.append(i)
        return [sorted_chunks[x] for x in indices]

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]
        retrieve_output = await self.batch_retrieve(task, **kwargs)
        try:
            selected_chunks = await self.context_select(
                task_query, retrieve_output.chunks
            )
        except Exception as e:
            import traceback

            traceback.print_exc()

        formatted_docs = []
        for chunk in selected_chunks:
            formatted_docs.append(f"{chunk.content}")

        formatted_docs = "\n\n".join(formatted_docs)
        system_instruction = self.get_system_instruction()
        query = f"{task.id}: {task.arguments['query']}"
        subqa = []
        for pt in task.parents:
            subq = f"{pt.id}: {pt.arguments['query']}"
            result = json.loads(pt.result)
            suba = str(result["response"])
            subqa.append(f"{subq}\n{suba}")
        subqa = "\n\n".join(subqa)
        request = f"{system_instruction}\nDocs:\n{formatted_docs}\nQuestions:\n{subqa}\n{query}"

        response = await self.llm.acall(request)
        task.update_memory("retriever", retrieve_output)
        task.result = json.dumps(
            {"query": task.arguments["query"], "response": response}, ensure_ascii=False
        )

        reporter.add_report_line(
            "reference",
            f"{query}_kag_retriever_result",
            retrieve_output,
            "FINISH",
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

    def get_system_instruction(self):
        """根据语言参数返回相应的系统指令"""
        if self.language == "zh":
            return """
作为解决复杂多跳问题的专家，我需要你帮助解决一个多跳问题。该问题已被分解为多个简单的单跳查询，其中每个问题可能依赖于前面问题的答案，即问题主体可能包含诸如"{{i.output}}"的内容，这意味着第i个子问题的答案。我将为你提供如何解决这些初步问题的见解或答案本身，这些对于准确解决问题至关重要。此外，我将提供与当前问题相关的文本摘录，建议你仔细阅读和理解。请以"思考："开始你的回答，在其中概述导致你结论的逐步思考过程。最后以"答案："结束，提供清晰准确的回答，不要添加任何额外的评论。

文档：
Sylvester
Sylvester是一个源自拉丁形容词silvestris的名字，意思是"森林的"或"野生的"，该词源自名词silva，意思是"林地"。古典拉丁语用i拼写。在古典拉丁语中，y代表与i不同的独立音素，不是拉丁语本土音素，而是用于转录外来词的音素。古典时期之后，y开始发音为i。用Sylv-代替Silv-的拼写始于古典时期之后。

伊利诺伊州尚佩恩县斯坦顿镇
斯坦顿镇是美国伊利诺伊州尚佩恩县的一个镇。根据2010年人口普查，其人口为505人，包含202个住房单元。

纽约州蒙特贝洛
蒙特贝洛（意大利语："美丽的山"）是美国纽约州罗克兰县拉马波镇的一个合并村庄。它位于萨芬北部、希尔伯恩东部、韦斯利山南部和艾尔蒙特西部。2010年人口普查时人口为4,526人。

埃里克·霍特
埃里克·霍特（1987年2月16日出生于纽约州蒙特贝洛）是一名美国足球运动员，目前是自由球员。

问题：
0：谁在公元800年被加冕为西方皇帝？
思考：提供的查理曼大帝段落表明他在800年被加冕为神圣罗马皇帝。答案：查理曼大帝。

1：{{0.output}}后来被称为什么？
思考：要确定{{0.output}}（查理曼大帝）后来被称为什么，我需要查看提供的关于查理曼大帝的段落。段落表明查理曼大帝也被称为"查理大帝"。答案：查理大帝

2：在{{0.output}}时代，姓氏Sylvester起源于哪种语言？
思考：问题询问在{{0.output}}（查理曼大帝）时代姓氏Sylvester的起源，查理曼大帝的统治时期是中世纪早期。关于Sylvester名字的段落说明它源自拉丁语。答案：拉丁语
"""
        else:  # 默认英文
            return """
As an adept specialist in resolving intricate multi-hop questions, I require your assistance in addressing a multi-hop question. The question has been segmented into multiple straightforward single-hop inquiries, wherein each question may depend on the responses to preceding questions, i.e., the question body may contain content such as "{{i.output}}", which means the answer of ith sub-question. I will furnish you with insights on how to address these preliminary questions, or the answers themselves, which are essential for accurate resolution. Furthermore, I will provide textual excerpts pertinent to the current question, which you are advised to peruse and comprehend thoroughly. Begin your reply with "Thought: ", where you'll outline the step-by-step thought process that leads to your conclusion. End with "Answer: " to deliver a clear and precise response without any extra commentary.
        
Docs:
Sylvester
Sylvester is a name derived from the Latin adjective silvestris meaning ``wooded ''or`` wild'', which derives from the noun silva meaning ``woodland ''. Classical Latin spells this with i. In Classical Latin y represented a separate sound distinct from i, not a native Latin sound but one used in transcriptions of foreign words. After the Classical period y came to be pronounced as i. Spellings with Sylv - in place of Silv - date from after the Classical period.

Stanton Township, Champaign County, Illinois
Stanton Township is a township in Champaign County, Illinois, USA. As of the 2010 census, its population was 505 and it contained 202 housing units.


Montebello, New York
Montebello (Italian: "Beautiful mountain") is an incorporated village in the town of Ramapo, Rockland County, New York, United States. It is located north of Suffern, east of Hillburn, south of Wesley Hills, and west of Airmont. The population was 4,526 at the 2010 census

Erik Hort
Erik Hort (born February 16, 1987 in Montebello, New York) is an American soccer player who is currently a Free Agent.


Questions:
0: Who was crowned emperor of the west in 800 CE?
Thought: One of the provided passage on Charlemagne indicates that he was crowned Holy Roman Emperor in 800. Answer: Charlemagne.

1: What was {{0.output}} later known as?
Thought: To determine what {{0.oputput}} (Charlemagne) was later known as, I need to review the provided passage about Charlemagne. The passage indicates that Charlemagne was also known as "Charles the Great." Answer: Charles the Great

2: What was the language from which the last name Sylvester originated during {{0.output}} era?
Thought: The question asks about the origin of the last name Sylvester during the time of the person {{0.output}}, which was Charlemagne, whose reign was in the Early Middle Ages. The passage about the name Sylvester states that it is derived from Latin. Answer: Latin
"""
