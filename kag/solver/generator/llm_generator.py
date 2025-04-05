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
from typing import Optional

from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    to_reference_list,
)
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@GeneratorABC.register("llm_generator")
class LLMGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        chunk_reranker: RerankByVector = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt
        self.chunk_reranker = chunk_reranker or RerankByVector.from_config(
            {
                "type": "rerank_by_vector",
            }
        )

    def invoke(self, query, context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        results = []
        rerank_queries = []
        chunks = []
        graph_data = []
        for task in context.gen_task(False):
            if isinstance(task.result, KAGRetrievedResponse) and self.chunk_reranker:
                rerank_queries.append(task.arguments["query"])
                if task.result.graph_data:
                    graph_data.append(task.result.graph_data)
                chunks.append(task.result.chunk_datas)
                if (
                    "i don't know" in task.result.summary.lower()
                    or task.result.summary == ""
                ):
                    continue
                results.append(
                    {
                        "task": task.arguments.get("query", ""),
                        "thought": task.thought,
                        "result": task.result.summary,
                    }
                )
            else:
                if task.result:
                    results.append(
                        {
                            "task": task.arguments.get("query", ""),
                            "thought": task.thought,
                            "result": task.result,
                        }
                    )
                else:
                    results.append(
                        {
                            "task": task.arguments.get("query", ""),
                            "thought": task.thought,
                        }
                    )
        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        refer_data = to_reference_list(
            prefix_id=0, retrieved_datas=rerank_chunks
        )
        content_json = {"step": results}
        if rerank_chunks:
            content_json["reference"] = refer_data
        content = json.dumps(content_json, ensure_ascii=False, indent=2)
        if reporter:
            reporter.add_report_line("generator", "input", content_json, "FINISH")
            reporter.add_report_line(
                "generator_reference", "reference", rerank_chunks, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference_all", "reference", refer_data, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference_graphs", "graph", graph_data, "FINISH"
            )
        return self.llm_client.invoke(
            {"query": query, "content": content},
            self.generated_prompt,
            segment_name="answer",
            tag_name="Final Answer",
            with_json_parse=False,
            **kwargs
        )
