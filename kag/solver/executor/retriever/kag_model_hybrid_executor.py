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
from typing import List, Optional
from kag.common.parser.logic_node_parser import (
    parse_logic_form_with_str,
    ParseLogicForm,
)
from kag.common.utils import (
    extract_specific_tag_content,
    extract_box_answer,
    search_plan_extraction,
)
from kag.interface import (
    ExecutorABC,
    RetrieverABC,
    RetrieverOutputMerger,
    RetrieverOutput,
    Task,
    LLMClient,
    PromptABC,
)
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.kag_hybrid_retrieval_executor import (
    KAGHybridRetrievalExecutor,
)

logger = logging.getLogger()


@ExecutorABC.register("kag_model_hybrid_retrieval_executor")
class KAGModelHybridRetrievalExecutor(KAGHybridRetrievalExecutor):
    def __init__(
        self,
        retrievers: List[RetrieverABC],
        merger: RetrieverOutputMerger,
        kag_sub_question_think_prompt: PromptABC,
        llm_module: LLMClient,
        **kwargs,
    ):
        super().__init__(
            retrievers=retrievers, merger=merger, llm_module=llm_module, **kwargs
        )
        self.kag_sub_question_think_prompt = kag_sub_question_think_prompt
        self.logic_node_parser = ParseLogicForm(schema=None, schema_retrieval=None)
        self.top_k = kwargs.get("top_k", 3)

    def do_main(self, task_query, tag_id, task, context, **kwargs):
        start_time = time.time()
        task_query = task.arguments["query"]
        logic_node = task.arguments.get("logic_form_node", None)
        # rewrite query
        flow_query = task_query
        for k, v in context.kwargs.get("step_answer", {}).items():
            if k in flow_query:
                flow_query = task_query.replace(k, v)
        logger.info(f"{task_query} rewrite query:{flow_query}")
        task.arguments["rewrite_query"] = flow_query

        step_id = task.name.lower().replace("step", "")

        messages = context.kwargs.get("messages", [])
        prompt_key = (
            f"Step{step_id}: {flow_query}"
            f"\nAction{step_id}: {logic_node.to_logical_form_str()}"
        )
        messages.append(
            {
                "role": "user",
                "content": self.kag_sub_question_think_prompt.build_prompt(
                    {"question": prompt_key}
                ),
            }
        )

        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        retriever_output = RetrieverOutput(
            retriever_method=self.schema().get("name", "")
        )

        num_turns = 0
        while num_turns < 10:
            num_turns += 1
            cur_turn_tag_name = f"begin_sub_kag_think_{task_query}_{num_turns}"
            subquestion_response = self.llm_module.__call__(
                prompt="",
                messages=messages,
                segment_name=tag_id,
                tag_name=cur_turn_tag_name,
                num_turns=num_turns,
                reporter=reporter,
            )

            if subquestion_response and "<search>" not in subquestion_response:
                messages.append(
                    {
                        "role": "assistant",
                        "content": subquestion_response,
                    }
                )
                if "<answer>" in subquestion_response:
                    answer_content = extract_specific_tag_content(
                        subquestion_response, "answer"
                    )[0]
                else:
                    answer_content = subquestion_response
                predict = extract_box_answer(answer_content)
                if not predict:
                    predict = answer_content
                step_answer = context.kwargs.get("step_answer", {})
                step_answer[f"#{step_id}"] = predict
                context.kwargs["step_answer"] = step_answer
                retriever_output.summary = predict
                if retriever_output.graphs and len(
                    retriever_output.graphs[0].get_all_spo()
                ):
                    context.variables_graph.merge_kg_graph(retriever_output.graphs[0])

                break
            else:
                if "<search>" in subquestion_response:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": subquestion_response,
                        }
                    )
                    search = search_plan_extraction(subquestion_response)
                    # 有时候会缺失</search>训练时需要优化<search>内容，不需要直接换行
                    if len(search) == 0:
                        search = subquestion_response.split("<search>")[-1].strip()

                    try:
                        sub_queries, logic_forms = parse_logic_form_with_str(search)
                        logic_forms = self.logic_node_parser.parse_logic_form_set(
                            logic_forms, sub_queries, task_query
                        )
                        if not logic_forms:
                            logic_node.sub_query = search
                            logic_forms = [logic_node]
                    except Exception as e:
                        logger.warning(
                            f"kag model think can not extra lf from {search} {e}"
                        )
                        logic_node.sub_query = search
                        logic_forms = [logic_node]

                    logger.info(
                        f"Query converted to logical form in {time.time() - start_time:.2f} seconds for task: {task_query}"
                    )

                    logger.info(f"Creating KAGFlow for task: {task_query}")
                    start_time = time.time()

                    logger.info(
                        f"KAGFlow created in {time.time() - start_time:.2f} seconds for task: {task_query}"
                    )

                    logger.info(f"Executing KAGFlow for task: {task_query}")
                    start_time = time.time()
                    try:
                        target_query = logic_forms[0].sub_query
                        cur_task = Task(
                            id=task.id,
                            name=task.name,
                            executor=task.executor,
                            parents=task.parents,
                            children=task.children,
                            arguments={
                                "query": target_query,
                                "logic_form_node": logic_forms[0],
                            },
                        )
                        retriever_output = self.do_retrieval(
                            task_query=target_query,
                            tag_id=cur_turn_tag_name,
                            task=cur_task,
                            context=context,
                            **kwargs,
                        )

                        recall_information_list = []
                        if retriever_output.graphs and len(
                            retriever_output.graphs[0].get_all_spo()
                        ):
                            spos = [
                                str(spo)
                                for spo in retriever_output.graphs[0].get_all_spo()
                            ]
                            spos_str = ";".join(spos)
                            recall_information_list.append(spos_str)
                        for chunk in retriever_output.chunks[: self.top_k]:
                            recall_information_list.append(chunk.content)
                        recall_str = (
                            "<references>"
                            + "\n\n".join(recall_information_list)
                            + "</references>"
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": recall_str,
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"kag flow exception! {e} search={search}", exc_info=True
                        )
                        self.report_content(
                            reporter,
                            cur_turn_tag_name,
                            f"failed_kag_retriever_{task_query}_{num_turns}",
                            f"{e}",
                            "INIT",
                            step=task.name,
                        )
                else:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": subquestion_response,
                        }
                    )

        context.kwargs["messages"] = messages
        return retriever_output

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
