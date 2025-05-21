import json
import os
import io
import csv
import logging
import time
import uuid

from typing import List, Any, Optional

from sympy import limit
from tenacity import stop_after_attempt, retry

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.config import get_default_chat_llm_config
from kag.common.parser.logic_node_parser import GetSPONode
from kag.interface import ExecutorABC, ExecutorResponse, LLMClient, Context
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.reporter_abc import ReporterABC
from kag.interface.solver.model.one_hop_graph import (
    ChunkData,
    RetrievedData,
    KgGraph,
)
from kag.interface import Task
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.utils import (
    get_history_qa,
)
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.kag_lf_rewriter import (
    KAGLFRewriter,
)

from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_flow import (
    KAGFlow,
)

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


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

        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "neo4j@openspg"
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def invoke(self, query, task: Task, context: Context, **kwargs):
        try_times = 1
        histroy_list = []
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
                task.result = str({"cypher": cypher, "result": "Cypher executed correctly and obtained the result"})
                return
            if not error_str:
                error_str = "no result"
            else:
                try_times += 1
            histroy_list.append({"cypher": cypher, "error": error_str})
        # 多次尝试都没有结果
        task.result = str(histroy_list[-1])

    def _get_cypher_result(self, cypher, limit=3):
        with self.driver.session(database="birdgraph") as session:
            # 执行查询
            try:
                result = session.run(cypher)
                records = [record for record in result][:limit]
            except Neo4jError as e:
                return "", str(e)

            # 获取查询结果
            rows = []
            for i, record in enumerate(records):
                if i >= limit:  # 只保存前 max_rows 行数据
                    break
                rows.append(dict(record))

            # 如果没有数据，直接返回空字符串
            if not rows:
                return "", None

            # 将数据组织为CSV格式
            output = io.StringIO()
            csv_writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(rows)

            # 返回CSV字符串
            return output.getvalue(), None

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
