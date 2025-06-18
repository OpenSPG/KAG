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
import asyncio
from typing import List, Optional

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import get_default_chat_llm_config, LogicFormConfiguration
from kag.common.parser.logic_node_parser import GetSPONode
from kag.interface import (
    ExecutorABC,
    RetrieverABC,
    RetrieverOutputMerger,
    RetrieverOutput,
    Task,
    Context,
    KgGraph,
    LLMClient,
    PromptABC,
    EntityData,
    SchemaUtils,
    Prop,
)
from kag.interface.solver.base_model import SPOEntity
from kag.interface.solver.planner_abc import format_task_dep_context
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.utils import init_prompt_with_fallback


@ExecutorABC.register("kag_hybrid_retrieval_executor")
class KAGHybridRetrievalExecutor(ExecutorABC):
    def __init__(
        self,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
        enable_summary=False,
        llm_module: LLMClient = None,
        summary_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        self.retrievers = retrievers
        self.merger = merger
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.summary_prompt = summary_prompt or init_prompt_with_fallback(
            "thought_then_answer", self.kag_project_config.biz_scene
        )

        self.enable_summary = enable_summary

        self.summary_chunks_num = kwargs.get("summary_chunk_num", 10)

    def inovke(
        self, query: str, task: Task, context: Context, **kwargs
    ) -> RetrieverOutput:
        outputs = []
        for retriever in self.retrievers:
            outputs.append(retriever.invoke(task, **kwargs))

        merged = self.merger.invoke(task, outputs, **kwargs)
        return merged

    async def ainvoke(
        self, query: str, task: Task, context: Context, **kwargs
    ) -> RetrieverOutput:
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]
        retrieval_tasks = []
        tag_id = f"{task_query}_begin_task"
        self.report_content(
            reporter,
            "thinker",
            tag_id,
            "",
            "FINISH",
        )
        for retriever in self.retrievers:
            self.report_content(
                reporter,
                tag_id,
                f"begin_sub_kag_retriever_{retriever.schema().get('name')}",
                "task_executing",
                "FINISH",
                component_name=retriever.schema().get("name"),
            )
            retrieval_tasks.append(
                asyncio.create_task(
                    retriever.ainvoke(
                        task, context=context, segment_name=tag_id, **kwargs
                    )
                )
            )
        outputs = await asyncio.gather(*retrieval_tasks)
        for output in outputs:
            self.do_data_report(
                output,
                reporter,
                tag_id,
                f"begin_sub_kag_retriever_{output.retriever_method}",
                "retrieved_info_digest",
            )
            spos = []
            for graph in output.graphs:
                spos += graph.get_all_spo()
            spos = list(set(spos))
            if spos:
                reporter.add_report_line(
                    tag_id,
                    f"end_sub_kag_retriever_{output.retriever_method}",
                    spos,
                    "FINISH",
                )

        merged = await self.merger.ainvoke(task, outputs, **kwargs)
        self.do_data_report(merged, reporter, tag_id, "kag_merger", "kag_merger_digest")
        if self.enable_summary:
            # summary
            chunks = merged.chunks[: self.summary_chunks_num]

            selected_rel = []
            for graph in merged.graphs:
                selected_rel += list(set(graph.get_all_spo()))
            selected_rel = list(set(selected_rel))
            formatted_docs = [str(rel) for rel in selected_rel]
            for doc in chunks:
                formatted_docs.append(f"{doc.content}")

            deps_context = format_task_dep_context(task.parents)
            summary_response = self.llm_module.invoke(
                {
                    "cur_question": task_query,
                    "questions": "\n\n".join(deps_context),
                    "docs": "\n\n".join(formatted_docs),
                },
                self.summary_prompt,
                with_json_parse=False,
                with_except=True,
                segment_name=tag_id,
                tag_name=f"begin_summary_{task_query}",
                **kwargs,
            )
            merged.summary = summary_response
            logical_node = task.arguments.get("logic_form_node", None)
            if logical_node and isinstance(logical_node, GetSPONode):
                target_answer =  merged.summary.split("Answer:")[1].strip()
                s_entities = context.variables_graph.get_entity_by_alias(logical_node.s.alias_name)
                if not s_entities and not logical_node.s.get_mention_name() and isinstance(logical_node.s, SPOEntity):
                    logical_node.s.entity_name = target_answer
                    context.kwargs[logical_node.s.alias_name] = logical_node.s
                o_entities = context.variables_graph.get_entity_by_alias(logical_node.o.alias_name)
                if not o_entities and not logical_node.o.get_mention_name() and isinstance(logical_node.o, SPOEntity):
                    logical_node.o.entity_name = target_answer
                    context.kwargs[logical_node.o.alias_name] = logical_node.o


                context.variables_graph.add_answered_alias(
                    logical_node.s.alias_name.alias_name, summary_response
                )
                context.variables_graph.add_answered_alias(
                    logical_node.p.alias_name.alias_name, summary_response
                )
                context.variables_graph.add_answered_alias(
                    logical_node.o.alias_name.alias_name, summary_response
                )

        self.report_content(
            reporter,
            "reference",
            f"{task_query}_kag_retriever_result",
            merged,
            "FINISH",
        )
        task.update_result(merged)
        return merged

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "Retriever",
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }

    def do_data_report(
        self,
        output: RetrieverOutput,
        reporter,
        segment_name,
        tag_id,
        show_info_digest,
        **kwargs,
    ):
        chunk_num = len(output.chunks)
        nodes_num = 0
        edges_num = 0
        merged_graph = KgGraph()
        for graph in output.graphs:
            merged_graph.merge_kg_graph(graph)
        nodes_num += len(merged_graph.get_all_entity())
        edges_num += len(merged_graph.get_all_spo())

        content = "kag_merger_digest_failed"
        if chunk_num > 0 or edges_num > 0 or nodes_num > 0:
            content = show_info_digest
        self.report_content(
            reporter,
            segment_name,
            tag_id,
            content,
            "FINISH",
            component_name=output.retriever_method,
            chunk_num=chunk_num,
            edges_num=edges_num,
            nodes_num=nodes_num,
            **kwargs,
        )
        all_spo = merged_graph.get_all_spo()
        chunk_graph = []
        for chunk in output.chunks:
            entity = EntityData(
                entity_id=chunk.chunk_id,
                name=chunk.title,
                node_type=chunk.properties.get("__labels__"),
            )
            entity_prop = dict(chunk.properties) if chunk.properties else {}
            entity_prop["content"] = chunk.content
            entity_prop["score"] = chunk.score
            entity.prop = Prop.from_dict(entity_prop, "Chunk", None)
            chunk_graph.append(entity)
        report_graph = all_spo + chunk_graph
        if len(report_graph):
            self.report_content(
                reporter,
                tag_id,
                f"spo_graph",
                report_graph,
                "FINISH",
            )
