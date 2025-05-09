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

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KAGRetrievedResponse,
    to_reference_list,
)
from kag.solver.utils import init_prompt_with_fallback
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector

from kag.interface import ExecutorABC, ExecutorResponse, LLMClient, Context, Task


def to_task_context_str(context):
    if not context or "task" not in context:
        return ""
    return f"""{context['name']}:{context['task']}
thought: {context['result']}.{context.get('thought', '')}"""


@GeneratorABC.register("bird_generator")
class BirdGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt

    @retry(stop=stop_after_attempt(3))
    def generate_answer(self, query, content, **kwargs):
        return self.llm_client.invoke(
            variables={
                "question": query,
                "schema": kwargs.get("graph_schema", ""),
                "history": kwargs.get("history", ""),
            },
            prompt_op=self.generated_prompt,
            with_json_parse=False,
        )

    def invoke(self, query, context: Context, **kwargs):
        return self.generate_answer(query=query, content="", **kwargs)
