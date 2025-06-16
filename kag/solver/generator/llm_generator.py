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

from tenacity import retry, stop_after_attempt

from kag.common.conf import KAGConfigAccessor, KAGConstants
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    to_reference_list,
)
from kag.solver.utils import init_prompt_with_fallback
from kag.common.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


def to_task_context_str(context):
    if not context or "task" not in context:
        return ""
    return f"""{context['name']}:{context['task']}
thought: {context['result']}.{context.get('thought', '')}"""


def extra_reference(references):
    return [
        {
            "content": reference["content"],
            "document_name": reference["document_name"],
            "id": reference["id"],
        }
        for reference in references
    ]


@GeneratorABC.register("llm_generator")
class LLMGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        chunk_reranker: RerankByVector = None,
        enable_ref=False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt
        self.chunk_reranker = chunk_reranker or RerankByVector.from_config(
            {
                "type": "rerank_by_vector",
            }
        )
        if enable_ref:
            self.with_out_ref_prompt = init_prompt_with_fallback(
                "without_refer_generator_prompt", kag_project_config.biz_scene
            )
            self.with_ref_prompt = init_prompt_with_fallback(
                "refer_generator_prompt", kag_project_config.biz_scene
            )
        self.enable_ref = enable_ref

    @retry(stop=stop_after_attempt(3))
    def generate_answer(self, query, content, refer_data, **kwargs):
        if not self.enable_ref:
            return self.llm_client.invoke(
                {"query": query, "content": content},
                self.generated_prompt,
                segment_name="answer",
                tag_name="Final Answer",
                with_json_parse=self.generated_prompt.is_json_format(),
                **kwargs,
            )
        if refer_data and len(refer_data):
            refer_data_str = json.dumps(refer_data, ensure_ascii=False, indent=2)
            return self.llm_client.invoke(
                {"query": query, "content": content, "ref": refer_data_str},
                self.with_ref_prompt,
                segment_name="answer",
                tag_name="Final Answer",
                with_json_parse=False,
                **kwargs,
            )
        return self.llm_client.invoke(
            {"query": query, "content": content},
            self.with_out_ref_prompt,
            segment_name="answer",
            tag_name="Final Answer",
            with_json_parse=False,
            **kwargs,
        )

    def invoke(self, query, context, **kwargs):
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        results = []
        rerank_queries = []
        chunks = []
        graph_data = context.variables_graph
        tasks = []
        for task in context.gen_task(False):
            tasks.append(task)
            if isinstance(task.result, KAGRetrievedResponse) and self.chunk_reranker:
                rerank_queries.append(
                    task.arguments.get("rewrite_query", task.arguments["query"])
                )
                chunks.append(task.result.chunk_datas)
            results.append(to_task_context_str(task.get_task_context()))

        rerank_chunks = self.chunk_reranker.invoke(query, rerank_queries, chunks)
        refer_retrieved_data = to_reference_list(
            prefix_id=0, retrieved_datas=rerank_chunks
        )
        content_json = {"step": results}
        if reporter:
            reporter.add_report_line(
                "generator", "final_generator_input", content_json, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference", "reference_chunk", rerank_chunks, "FINISH"
            )
            reporter.add_report_line(
                "generator_reference_all",
                "reference_ref_format",
                refer_retrieved_data,
                "FINISH",
            )
            reporter.add_report_line(
                "generator_reference_graphs", "reference_graph", graph_data, "FINISH"
            )
        refer_data = extra_reference(refer_retrieved_data)
        if len(refer_data) and (not self.enable_ref):
            content_json["reference"] = refer_data

        content = json.dumps(content_json, ensure_ascii=False, indent=2)
        if not self.enable_ref:
            refer_data = [
                f"Title:{x['document_name']}\n{x['content']}" for x in refer_data
            ]
            refer_data = "\n\n".join(refer_data)
            thoughts = "\n\n".join(results)
            content = f"""
Docs:
{refer_data}

Step by Step Analysis:
{thoughts}

            """
        return self.generate_answer(
            query=query, content=content, refer_data=refer_data, **kwargs
        )
