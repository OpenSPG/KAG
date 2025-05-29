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
import io
import csv

from tenacity import retry, stop_after_attempt

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import GeneratorABC, LLMClient, PromptABC
from kag.solver.utils import init_prompt_with_fallback
from kag.examples.bird_graph.solver.cypher.rewrite_cypher import rewrite_cypher
from kag.interface import ExecutorABC, ExecutorResponse, LLMClient, Context, Task
from kag.examples.bird_graph.solver.cypher.cypher_execute_engine import (
    CypherExecuteEngine,
)


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
        generated_return_column_prompt: PromptABC,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt
        self.generated_return_column_prompt = generated_return_column_prompt
        self.fix_cypher_prompt = init_prompt_with_fallback(
            "fix_cypher", KAG_PROJECT_CONF.biz_scene
        )

    @retry(stop=stop_after_attempt(3))
    async def generate_answer(self, query, content, **kwargs):
        return await self.llm_client.ainvoke(
            variables={
                "question": query,
                "schema": kwargs.get("graph_schema", ""),
                "history": kwargs.get("history", ""),
            },
            prompt_op=self.generated_prompt,
            with_json_parse=False,
        )

    @retry(stop=stop_after_attempt(3))
    async def generate_return_column(self, query, content, **kwargs):
        return await self.llm_client.ainvoke(
            variables={
                "question": query,
                "schema": kwargs.get("graph_schema", ""),
                "history": kwargs.get("history", ""),
            },
            prompt_op=self.generated_return_column_prompt,
            with_json_parse=False,
        )

    def invoke(self, query, context, **kwargs):
        pass

    async def ainvoke(self, query, context, **kwargs):
        return await self._ainvoke(query, **kwargs)

    async def _ainvoke(self, query, **kwargs):
        history = []
        try_times = 3
        cypher = None
        r_cypher = None
        while try_times > 0:
            try_times -= 1
            cypher = await self.generate_answer(
                query=query, content="", history=str(history), **kwargs
            )
            if "i don't know" in cypher or len(cypher) == 0:
                continue
            # check return column
            # return_column = await self.generate_return_column(
            #     query=query, content="", history=str(history), **kwargs
            # )
            # print(f"return_column={return_column}")
            # rewrite cypher by cypher skeleton - only return_column
            r_cypher = rewrite_cypher(cypher, [])
            if r_cypher is None:
                print(f"r_cypher is empty. cypher = {cypher}")
                continue
            # get cypher result
            cypher_rst, error_str = await self._get_cypher_result(r_cypher)
            if cypher_rst:
                break
            if error_str is None:
                error_str = "Cypher execution completed, but with no results"
            history.append({"cypher": r_cypher, "error": error_str})
        print(f"cypher:{cypher}\n,rewrite_cypher:{r_cypher}\n")
        return await self.refine_cypher(query, r_cypher, **kwargs)

    async def refine_cypher(self, query, cypher, **kwargs):
        return cypher
        # return await self.llm_client.ainvoke(
        #     variables={
        #         "question": query,
        #         "schema": kwargs.get("graph_schema", ""),
        #         "cypher": cypher,
        #     },
        #     prompt_op=self.fix_cypher_prompt,
        #     with_json_parse=False,
        # )

    async def _get_cypher_result(self, cypher, limit=3):
        # 使用异步会话执行查询
        rows, error_info = await CypherExecuteEngine().async_run(cypher, 9999)

        # 如果没有数据，直接返回空字符串
        if not rows:
            return "", None

        # 将数据组织为CSV格式
        # output = io.StringIO()
        # csv_writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        # csv_writer.writeheader()
        # csv_writer.writerows(rows)

        # 返回CSV字符串
        return rows, None
