import csv
import io
import json
import logging
from typing import List
import asyncio
from sympy import limit

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.config import get_default_chat_llm_config
from kag.examples.bird_graph.solver.cypher.cypher_execute_engine import (
    CypherExecuteEngine,
)
from kag.interface import ExecutorABC, LLMClient, Context
from kag.interface import Task
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


@ExecutorABC.register("bird_cypher_gen")
class BirdCypherGenRunner(ExecutorABC):
    """
    cypher生成
    """

    def __init__(self, llm: LLMClient = None, **kwargs):
        super().__init__(**kwargs)
        self.nl2cypher_prompt = init_prompt_with_fallback(
            "nl2cypher", KAG_PROJECT_CONF.biz_scene
        )
        self.refin_cypher_prompt = init_prompt_with_fallback(
            "refine_cypher", KAG_PROJECT_CONF.biz_scene
        )
        self.llm_client: LLMClient = llm or LLMClient.from_config(
            get_default_chat_llm_config()
        )

    def invoke(self, query, task: Task, context: Context, **kwargs):
        try_times = 1
        histroy_list = []
        cypher = None
        while try_times > 0:
            try_times -= 1
            cypher = self.llm_client.invoke(
                variables={
                    "question": task.arguments["query"],
                    "schema": str(kwargs.get("graph_schema", "")),
                    "goal": query,
                    "old_cypher": self._get_old_cypher(task.parents),
                    "history": str(histroy_list),
                },
                prompt_op=self.nl2cypher_prompt,
                with_json_parse=False,
            )
            cypher_result, error_str = self._get_cypher_result(cypher)
            if cypher_result:
                task.result = {"cypher": cypher, "result": cypher_result}
                return
            if not error_str:
                task.result = {"cypher": cypher, "result": []}
                error_str = "no result"
            else:
                try_times += 1
            histroy_list.append({"cypher": cypher, "error": error_str})
        # 多次尝试都没有结果
        task.result = {"cypher": cypher, "result": []}

    def _get_cypher_result(self, cypher, limit=9999):
        rows = asyncio.run(CypherExecuteEngine().async_run(cypher))
        # 如果没有数据，直接返回空字符串
        if not rows:
            return [], None

        # 将数据组织为CSV格式
        # output = io.StringIO()
        # csv_writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        # csv_writer.writeheader()
        # csv_writer.writerows(rows)

        # 返回CSV字符串
        return rows[0], None

    # def _refein_cypher(self, cypher, query: str, task: Task):
    #     """
    #     反思Cypher的结果
    #     """
    #     try_times = 3
    #     while try_times > 0:
    #         try_times -= 1
    #         cypher_result, error_str = self._get_cypher_result(cypher)
    #         if error_str:
    #             cypher_result = error_str
    #         new_cypher = self.llm_client.invoke(
    #             variables={
    #                 "question": task.arguments["query"],
    #                 "schema": str(self.graph_schema),
    #                 "goal": query,
    #                 "old_cypher": cypher,
    #                 "cypher_result": cypher_result,
    #             },
    #             prompt_op=self.refin_cypher_prompt,
    #             with_json_parse=False,
    #         )
    #         if new_cypher is True:
    #             return cypher
    #         cypher = new_cypher
    #     return None

    def _get_old_cypher(self, parents: List[Task]):
        rst_str = ""
        for i, task in enumerate(parents):
            rst_str += f"\nsub_question_{i+1}: {task.arguments['query']}\n```cypher\n{task.result}```"
        rst_str = rst_str.strip()
        if len(rst_str) <= 0:
            return "None"
        return rst_str

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "CypherGenerator",
            "description": "Convert natural language into Cypher and check it.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
