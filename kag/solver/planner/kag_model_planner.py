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
from typing import List, Optional

from kag.common.parser.logic_node_parser import parse_logic_form_with_str, ParseLogicForm, GetSPONode, MathNode, \
    DeduceNode, GetNode
from kag.interface import PlannerABC, Task, LLMClient, PromptABC, Context


def _get_dep_task_id(logic_forms):
    all_alias_index_map = {}

    def add_index_map(alias, index):
        if alias in all_alias_index_map.keys():
            return
        all_alias_index_map[alias] = index

    for i, logic_form in enumerate(logic_forms):
        if isinstance(logic_form, GetSPONode):
            add_index_map(logic_form.s.alias_name.alias_name, i)
            add_index_map(logic_form.p.alias_name.alias_name, i)
            add_index_map(logic_form.o.alias_name.alias_name, i)
        elif isinstance(logic_form, MathNode) or isinstance(logic_form, DeduceNode):
            add_index_map(logic_form.alias_name, i)

    return all_alias_index_map


def _get_task_dep(index, logic_node, dep_task):
    ret = []

    def add_dep_by_index(alias_name):
        alias_index = dep_task[alias_name]
        if alias_index < index:
            ret.append(alias_index)

    if isinstance(logic_node, GetSPONode):
        add_dep_by_index(logic_node.s.alias_name.alias_name)
        add_dep_by_index(logic_node.p.alias_name.alias_name)
        add_dep_by_index(logic_node.o.alias_name.alias_name)
    if isinstance(logic_node, GetNode):
        return []

    if isinstance(logic_node, MathNode) or isinstance(logic_node, DeduceNode):
        for alias in dep_task.keys():
            if alias in logic_node.content:
                ret.append(dep_task[alias])
    return ret


@PlannerABC.register("kag_model_planner")
class KAGModelPlanner(PlannerABC):
    """Iterative planner that uses LLM to generate task plans based on context and available executors.

    Args:
        llm (LLMClient): Language model client for plan generation
        plan_prompt (PromptABC): Prompt template for planning requests
    """

    def __init__(self, llm: LLMClient, system_prompt: PromptABC, clarification_prompt, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

        self.logic_node_parser = ParseLogicForm(
            schema=None, schema_retrieval=None
        )
        self.system_prompt = system_prompt
        self.clarification_prompt = clarification_prompt
    async def ainvoke(self, query, **kwargs) -> List[Task]:
        """Asynchronously generates task plan using LLM.

        Args:
            query: User query to generate plan for
            **kwargs: Additional parameters including:
                - context (Context): Execution context
                - executors (list): Available executors for task planning

        Returns:
            List[Task]: Generated task sequence
        """
        context: Optional[Context] = kwargs.get("context", None)
        messages = context.kwargs.get("messages", [])
        messages.append({"role": "system", "content": self.system_prompt.build_prompt({})})
        messages.append({
            "role": "user",
            "content": self.clarification_prompt.build_prompt({"question": query}),
        })
        logic_form_response = await self.llm.acall(prompt="", messages=messages,
                                                   segment_name="thinker",
                                                   tag_name=f"Static planning",
                                                   **kwargs)
        messages.append({
            "role": "assistant",
            "content": logic_form_response,
        })
        context.kwargs["messages"] = messages
        logic_form_str = logic_form_response.split("</think>")[-1].strip().replace("<answer>", "").replace("</answer>",
                                                                                                           "").strip()

        sub_queries, logic_forms = parse_logic_form_with_str(logic_form_str)
        logic_forms = self.logic_node_parser.parse_logic_form_set(logic_forms, sub_queries, query)

        tasks_dep = {}
        for i, logic_form in enumerate(logic_forms):
            task_deps = [] if i == 0 else [i - 1]
            tasks_dep[i] = {
                "name": f"Step{i + 1}",
                "executor": logic_form.operator,
                "dependent_task_ids": task_deps,
                "arguments": {
                    "query": logic_form.sub_query,
                    "logic_form_node": logic_form,
                    "is_need_rewrite": False,
                },
            }
        return Task.create_tasks_from_dag(tasks_dep)
