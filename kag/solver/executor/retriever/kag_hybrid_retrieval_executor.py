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
import time
import logging
from collections import defaultdict
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from tenacity import stop_after_attempt, retry, wait_exponential

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import get_default_chat_llm_config
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
    Prop,
)
from kag.interface.solver.base_model import SPOEntity
from kag.interface.solver.planner_abc import format_task_dep_context
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


def _wrapped_invoke(retriever, task, context, segment_name, kwargs):
    start_time = time.time()
    output = retriever.invoke(
        task, context=context, segment_name=segment_name, **kwargs
    )
    elapsed_time = time.time() - start_time
    return output, elapsed_time


@ExecutorABC.register("kag_hybrid_retrieval_executor")
class KAGHybridRetrievalExecutor(ExecutorABC):
    def __init__(
        self,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
        context_select_llm: LLMClient = None,
        context_select_prompt: PromptABC = None,
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

        self.context_select_llm = context_select_llm or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.context_select_prompt = context_select_prompt or PromptABC.from_config(
            {"type": "context_select_prompt"}
        )
        self.with_llm_select = kwargs.get("with_llm_select", True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
    def context_select_call(self, variables):
        return self.context_select_llm.invoke(variables, self.context_select_prompt)

    def context_select(self, query: str, sorted_chunks):
        chunks = []
        for idx, item in enumerate(sorted_chunks):
            chunks.append({"idx": idx, "content": item.content})
        variables = {"question": query, "context": chunks}
        response = self.context_select_llm.invoke(variables, self.context_select_prompt)
        selected_context = response["context"]
        indices = []
        if len(selected_context) > 0:
            indices.extend(selected_context)
        for i in range(min(4, len(sorted_chunks))):
            if i not in indices:
                indices.append(i)
        return [sorted_chunks[x] for x in indices]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
    def summary_answer(
        self, tag_id, task_query, deps_context, formatted_docs, **kwargs
    ):
        return self.llm_module.invoke(
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

    def do_retrieval(
        self, task_query, tag_id, task, context: Context, **kwargs
    ) -> RetrieverOutput:
        start_time = time.time()
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)

        # Step 1: Group retrievers by their 'priority' attribute.
        # This allows us to execute them in priority order.
        priority_groups = defaultdict(list)
        for retriever in self.retrievers:
            # Default to priority 1 if not explicitly set
            priority = getattr(retriever, "priority", 1)
            priority_groups[priority].append(retriever)

        # Step 2: Sort the priorities in ascending order (lower number = higher priority)
        sorted_priorities = sorted(priority_groups.keys())

        retrieved_data = RetrieverOutput()

        # Step 3: Process each group in order of increasing priority
        for priority in sorted_priorities:
            group = priority_groups[priority]
            logger.debug(f"Executing retrievers with priority={priority}")

            outputs = []  # To collect output from each retriever
            # Use a thread pool executor to run all retrievers in this group concurrently
            with ThreadPoolExecutor(max_workers=len(group)) as executor:
                futures = []
                for retriever in group:
                    # Report the beginning of each sub-retriever execution
                    self.report_content(
                        reporter,
                        tag_id,
                        f"begin_sub_kag_retriever_{retriever.name}",
                        "task_executing",
                        "FINISH",
                        component_name=retriever.name,
                    )
                    # Record start time before submitting the task
                    start_time = time.time()
                    # Prepare function and submit to thread pool
                    func = partial(
                        _wrapped_invoke,
                        retriever,
                        task,
                        context,
                        tag_id,
                        kwargs.copy(),
                    )
                    future = executor.submit(func)
                    # Save future, retriever, and start_time together
                    futures.append((future, retriever))

                # Collect results from each future
                for future, retriever in futures:
                    try:
                        output, elapsed_time = future.result()  # Wait for result

                        # Log the elapsed time for this retriever
                        logger.info(
                            f"Retriever {retriever.name} executed in {elapsed_time:.2f} seconds"
                        )
                        outputs.append(output)

                        # Log data report after successful execution
                        self.do_data_report(
                            output,
                            reporter,
                            tag_id,
                            f"begin_sub_kag_retriever_{output.retriever_method}",
                            "retrieved_info_digest",
                        )

                        # Extract SPOs (Subject-Predicate-Object triples) from output graphs
                        spos = []
                        for graph in output.graphs:
                            spos += graph.get_all_spo()
                        spos = list(set(spos))  # Deduplicate

                        # Add report line if there are any SPOs
                        if reporter and spos:
                            reporter.add_report_line(
                                tag_id,
                                f"end_sub_kag_retriever_{output.retriever_method}",
                                spos,
                                "FINISH",
                            )
                    except Exception as e:
                        logger.error(f"Error executing retriever {retriever}: {e}")
            if len(outputs) > 1:
                merged_start_time = time.time()
                retrieved_data = self.merger.invoke(task, outputs, **kwargs)
                logger.debug(
                    f"kag hybrid retrieval {task_query} priority {priority} merged cost={time.time() - merged_start_time}"
                )
            elif len(outputs) == 1:
                retrieved_data = outputs[0]
            else:
                retrieved_data = RetrieverOutput()
            # judge is break
            if (
                (retrieved_data.graphs and retrieved_data.graphs[0].get_all_spo())
                or retrieved_data.chunks
                or retrieved_data.docs
            ):
                break
        # Log total cost time for all retrievers
        logger.debug(
            f"kag hybrid retrieval {task_query} retriever cost={time.time() - start_time}"
        )

        self.do_data_report(
            retrieved_data, reporter, tag_id, "kag_merger", "kag_merger_digest"
        )

        return retrieved_data

    def do_summary(
        self,
        task_query,
        tag_id,
        task,
        retrieved_data: RetrieverOutput,
        context: Context,
        **kwargs,
    ):
        if not self.enable_summary:
            return retrieved_data
        # summary
        selected_rel = []
        for graph in retrieved_data.graphs:
            selected_rel += list(set(graph.get_all_spo()))
        selected_rel = list(set(selected_rel))
        formatted_docs = [str(rel) for rel in selected_rel]
        if retrieved_data.chunks:
            if self.with_llm_select:
                try:
                    selected_chunks = self.context_select(
                        task_query, retrieved_data.chunks
                    )
                except Exception as e:
                    logger.warning(
                        f"select context failed {e}, we use default top 10 to summary",
                        exc_info=True,
                    )
                    selected_chunks = retrieved_data.chunks[:10]
            else:
                selected_chunks = retrieved_data.chunks[:10]
            for doc in selected_chunks:
                formatted_docs.append(f"{doc.content}")

        deps_context = format_task_dep_context(task.parents)
        summary_start_time = time.time()
        summary_response = self.summary_answer(
            tag_id=tag_id,
            task_query=task_query,
            deps_context=deps_context,
            formatted_docs=formatted_docs,
            **kwargs,
        )
        retrieved_data.summary = summary_response
        logger.debug(
            f"kag hybrid retrieval {task_query} summary cost={time.time() - summary_start_time}"
        )
        return retrieved_data

    def do_main(self, task_query, tag_id, task, context, **kwargs):
        retrieved_data = self.do_retrieval(task_query, tag_id, task, context, **kwargs)
        retrieved_data = self.do_summary(
            task_query, tag_id, task, retrieved_data, context, **kwargs
        )
        return retrieved_data

    def invoke(self, query, task, context: Context, **kwargs) -> RetrieverOutput:
        start_time = time.time()
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        task_query = task.arguments["query"]

        tag_id = f"{task_query}_begin_task"
        self.report_content(reporter, "thinker", tag_id, "", "INIT", step=task.name)
        try:
            try:
                retrieved_data = self.do_main(
                    task_query, tag_id, task, context, **kwargs
                )
            except Exception as e:
                logger.warning(f"kag hybrid retrieval failed! {e}", exc_info=True)
                retrieved_data = RetrieverOutput(
                    retriever_method=self.schema().get("name", ""), err_msg=str(e)
                )

            self.report_content(
                reporter,
                "reference",
                f"{task_query}_kag_retriever_result",
                retrieved_data,
                "FINISH",
            )

            retrieved_data.task = task
            logical_node = task.arguments.get("logic_form_node", None)
            if (
                logical_node
                and isinstance(logical_node, GetSPONode)
                and retrieved_data.summary
            ):
                if isinstance(retrieved_data.summary, str):
                    target_answer = retrieved_data.summary.split("Answer:")[-1].strip()
                    s_entities = context.variables_graph.get_entity_by_alias(
                        logical_node.s.alias_name
                    )
                    if (
                        not s_entities
                        and not logical_node.s.get_mention_name()
                        and isinstance(logical_node.s, SPOEntity)
                    ):
                        logical_node.s.entity_name = target_answer
                        context.kwargs[logical_node.s.alias_name] = logical_node.s
                    o_entities = context.variables_graph.get_entity_by_alias(
                        logical_node.o.alias_name
                    )
                    if (
                        not o_entities
                        and not logical_node.o.get_mention_name()
                        and isinstance(logical_node.o, SPOEntity)
                    ):
                        logical_node.o.entity_name = target_answer
                        context.kwargs[logical_node.o.alias_name] = logical_node.o

                context.variables_graph.add_answered_alias(
                    logical_node.s.alias_name.alias_name, retrieved_data.summary
                )
                context.variables_graph.add_answered_alias(
                    logical_node.p.alias_name.alias_name, retrieved_data.summary
                )
                context.variables_graph.add_answered_alias(
                    logical_node.o.alias_name.alias_name, retrieved_data.summary
                )

            task.update_result(retrieved_data)
            logger.debug(
                f"kag hybrid retrieval {task_query} cost={time.time() - start_time}"
            )
            return retrieved_data
        finally:
            self.report_content(
                reporter,
                "thinker",
                tag_id,
                "",
                "FINISH",
                step=task.name,
                overwrite=False,
            )

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
            entity_prop["content"] = f"{chunk.content[:10]}..."
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
