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

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    to_reference_list,
)
from kag.solver.utils import init_prompt_with_fallback
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@GeneratorABC.register("llm_generator")
class LLMGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        chunk_reranker: RerankByVector = None,
        enable_ref = False,
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
        if enable_ref:
            self.with_out_ref_prompt = init_prompt_with_fallback("without_refer_generator_prompt", KAG_PROJECT_CONF.biz_scene)
            self.with_ref_prompt = init_prompt_with_fallback("refer_generator_prompt", KAG_PROJECT_CONF.biz_scene)
        self.enable_ref = enable_ref
    def invoke(self, query, context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        results = []
        rerank_queries = []
        chunks = []
        graph_data = context.variables_graph
        for task in context.gen_task(False):
            if isinstance(task.result, KAGRetrievedResponse) and self.chunk_reranker:
                rerank_queries.append(task.arguments["query"])
                chunks.append(task.result.chunk_datas)
            results.append(task.get_task_context())

        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        refer_data = to_reference_list(
            prefix_id=0, retrieved_datas=rerank_chunks
        )
        content_json = {"step": results}
        if reporter:
            reporter.add_report_line("generator", "final_generator_input", content_json, "FINISH")
            reporter.add_report_line(
                "generator_reference", "reference_chunk", rerank_chunks, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference_all", "reference_ref_format", refer_data, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference_graphs", "reference_graph", graph_data, "FINISH"
            )

        if len(refer_data) and (not self.enable_ref):
            content_json["reference"] = refer_data
        content = json.dumps(content_json, ensure_ascii=False, indent=2)
        if not self.enable_ref:

            return self.llm_client.invoke(
                {"query": query, "content": content},
                self.generated_prompt,
                segment_name="answer",
                tag_name="Final Answer",
                with_json_parse=False,
                **kwargs
            )
        if len(refer_data):
            refer_data_str = json.dumps(refer_data, ensure_ascii=False, indent=2)
            content = json.dumps(content_json, ensure_ascii=False, indent=2)
            return self.llm_client.invoke(
                {"query": query, "content": content, "ref": refer_data_str},
                self.with_ref_prompt,
                segment_name="answer",
                tag_name="Final Answer",
                with_json_parse=False,
                **kwargs
            )
        return self.llm_client.invoke(
                {"query": query, "content": content},
                self.with_out_ref_prompt,
                segment_name="answer",
                tag_name="Final Answer",
                with_json_parse=False,
                **kwargs
            )
