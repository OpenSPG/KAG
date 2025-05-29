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
from kag.interface import (
    ExecutorABC,
    RetrieverABC,
    RetrieverOutputMerger,
    RetrieverOutput,
    Task,
    Context,
)
from kag.interface.solver.reporter_abc import ReporterABC


@ExecutorABC.register("kag_hybrid_retrieval_executor")
class KAGHybridRetrievalExecutor(ExecutorABC):
    def __init__(
        self, retrievers: List[RetrieverABC], merger: RetrieverOutputMerger, **kwargs
    ):
        super().__init__(**kwargs)
        self.retrievers = retrievers
        self.merger = merger

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
        tag_id = f"{task_query}_begin_kag_retriever"
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
                asyncio.create_task(retriever.ainvoke(task, **kwargs))
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
        for graph in output.graphs:
            nodes_num += len(graph.nodes)
            edges_num += len(graph.edges)
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
