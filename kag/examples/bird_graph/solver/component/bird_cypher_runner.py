import json
import os
import logging
import time
import uuid

from typing import List, Any, Optional

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


logger = logging.getLogger()


@ExecutorABC.register("bird_cypher_runner")
class BirdCypherRunner(ExecutorABC):
    """
    cypher生成
    """

    def __init__(self, llm: LLMClient = None, **kwargs):
        super().__init__(**kwargs)
        self.nl2cypher_prompt = init_prompt_with_fallback(
            "nl2cypher", KAG_PROJECT_CONF.biz_scene
        )
        self.llm_client: LLMClient = llm or LLMClient.from_config(
            get_default_chat_llm_config()
        )

        NEO4J_URI = "bolt://localhost:7687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "neo4j@openspg"
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def invoke(self, query, task: Task, context: Context, **kwargs):
        cypher = self.llm_client.invoke(
            variables={
                "question": task.arguments["query"],
                "schema": str(kwargs.get("graph_schema", "")),
            },
            prompt_op=self.nl2cypher_prompt,
            with_json_parse=False,
        )
        print(cypher)
        with self.driver.session() as session:
            result = session.run(cypher)
            for x in result:
                print(x)
        return cypher

    def schema(self) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": "CypherRunner",
            "description": "Convert natural language into Cypher and execute it",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
