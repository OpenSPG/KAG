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
import logging
from typing import List, Dict

from neo4j.graph import Path, Node, Relationship

from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface import ExecutorABC
from kag.interface import LLMClient
from kag.open_benchmark.prqa.solver.prompt.prompt_message import (
    path_messages,
    filter_messages,
    multi_hop_messages,
)

logger = logging.getLogger()

cypher_tools = [
    {
        "type": "function",
        "function": {
            "name": "run_cypher_query",
            "description": "Get subgraph response for provided cypher query",
            "parameters": {
                "type": "object",
                "properties": {"cypher_query": {"type": "string"}},
                "required": ["cypher_query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]


@ExecutorABC.register("kag_prqa_executor")
class PrqaExecutor(ExecutorABC):
    """The PRQA executor is used to invoke llm to generate cypher and neo4j to execute cypher statements

    Args:
       llm (LLMClient): Language model client for plan generation
       neo4j_user (str): the username of neo4j which is registered in kag_config.yaml
       neo4j_password (str): the password of neo4j which is registered in kag_config.yaml
    """

    def __init__(self, llm: LLMClient, neo4j_user: str, neo4j_password: str, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.neo4j_client = Neo4jClient(
            uri="neo4j://localhost:7687",
            user=neo4j_user,
            password=neo4j_password,
            database="prqa",
        )
        self.handlers = {
            "type1": self.handle_type1_path,
            "type2": self.handle_type2_filter,
            "type3": self.handle_type3_list,
        }
        relationships_result = self.get_relationships()
        self.update_schema_messages(filter_messages, relationships_result)
        self.update_schema_messages(multi_hop_messages, relationships_result)

    def send_cypher_messages(self, messages):
        response = self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=messages,
            tools=cypher_tools,
            tool_choice={"type": "function", "function": {"name": "run_cypher_query"}},
        )
        return response.choices[0].message

    def generate_cypher(self, question: str, query_type: int = 1) -> str:
        """不带缓存的Cypher生成"""
        try:
            if query_type == 1:
                message_list = path_messages.copy()
            elif query_type == 2:
                message_list = filter_messages.copy()
            elif query_type == 3:
                message_list = multi_hop_messages.copy()

            else:
                raise ValueError(f"未知的查询类型: {query_type}")
            new_message = {"role": "user", "content": str(question)}
            message_list.append(new_message)

            completion_1 = self.send_cypher_messages(message_list)

            if not completion_1.tool_calls:
                raise ValueError(f"{question} 查询失败，此时tool_calls 为空或为 None，无法继续处理")
            tool = completion_1.tool_calls[0]
            args = json.loads(tool.function.arguments)
            cypher_query = args.get("cypher_query")

            return cypher_query

        except Exception as e:
            logger.error(f"生成 Cypher 查询失败: {str(e)}", exc_info=True)
            return ""

    # ---------- 第一类处理：路径查询 ----------
    def handle_type1_path(self, question: str) -> List:
        """处理明确路径查询"""
        try:
            cypher = self.generate_cypher(question, query_type=1)
            raw_result = self.execute_cypher(cypher)

            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"路径查询失败: {str(e)}")
            return []

    # ---------- 第二类处理：过滤型查询 ----------
    def handle_type2_filter(self, question: str) -> List:
        """处理带排除条件的查询"""
        try:
            cypher = self.generate_cypher(question, query_type=2)
            raw_result = self.execute_cypher(cypher)
            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"过滤查询失败: {str(e)}")
            return []

    # ---------- 第三类处理：多结果列表查询 ----------
    def handle_type3_list(self, question: str) -> List:
        """处理需要遍历多个结果的查询"""
        try:
            cypher = self.generate_cypher(question, query_type=3)
            raw_result = self.execute_cypher(cypher)
            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"列表查询失败: {str(e)}")
            return []

    def execute_cypher(self, cypher: str) -> List:
        """增强的查询执行"""
        try:
            raw = self.neo4j_client.run_cypher_query("prqa", cypher)
            if not isinstance(raw, list):
                logger.error(f"无效的查询结果类型: {type(raw)}")
                return []
            return self.standardize_result(raw)
        except Exception as e:
            logger.error(f"查询执行失败: {cypher} - {str(e)}")
            return []

    @staticmethod
    def standardize_result(data: List) -> List:
        """增强标准化方法"""
        processed = []
        for record in data:
            try:
                clean_record = {}
                for key, value in record.items():
                    if isinstance(value, Path):
                        path_data = {
                            "nodes": [
                                {
                                    "element_id": (
                                        node.element_id
                                        if hasattr(node, "element_id")
                                        else None
                                    ),
                                    "labels": list(node.labels),
                                    "properties": {
                                        k: v
                                        for k, v in node.items()
                                        if k != "_name_vector"
                                    },
                                }
                                for node in value.nodes
                            ],
                            "relationships": [
                                {
                                    "element_id": (
                                        rel.element_id
                                        if hasattr(rel, "element_id")
                                        else None
                                    ),
                                    "type": rel.type,
                                    "start_node": rel.start_node.element_id,
                                    "end_node": rel.end_node.element_id,
                                    "properties": {
                                        k: v
                                        for k, v in rel.items()
                                        if k != "_name_vector"
                                    },
                                }
                                for rel in value.relationships
                            ],
                        }
                        clean_record[key] = path_data
                    elif isinstance(value, (Node, Relationship)):
                        element_type = {
                            Node: {
                                "element_id": value.element_id,
                                "labels": list(value.labels),
                                "properties": {
                                    k: v
                                    for k, v in value.items()
                                    if k != "_name_vector"
                                },
                            },
                            Relationship: {
                                "element_id": value.element_id,
                                "type": value.type,
                                "start_node": value.start_node.element_id,
                                "end_node": value.end_node.element_id,
                                "properties": {
                                    k: v
                                    for k, v in value.items()
                                    if k != "_name_vector"
                                },
                            },
                        }[type(value)]
                        clean_record[key] = element_type
                    else:
                        clean_record[key] = value
                processed.append(clean_record)
            except Exception as e:
                logger.error(f"记录处理异常: {str(e)}")
        return processed

    @staticmethod
    def process_path_result(path_data: List[Dict]) -> List[str]:
        """安全处理包含多层结构的路径数据"""
        all_sentences = []
        try:
            for path in path_data:
                sentences = []
                # 提取核心路径数据（处理p字段嵌套）
                path_container = path.get("p", {})
                raw_nodes = path_container.get("nodes", [])
                raw_rels = path_container.get("relationships", [])

                node_map = {}
                for node in raw_nodes:
                    if not isinstance(node, dict):
                        continue

                    node_id = node.get("element_id")
                    if not node_id:
                        continue

                    props = node.get("properties", {})
                    node_name = (
                        props.get("name")
                        or props.get("title")
                        or f"未知节点_{node_id[-4:]}"
                    )
                    node_map[node_id] = node_name

                seen_relationships = set()
                for rel in raw_rels:
                    if not isinstance(rel, dict):
                        continue

                    # rel_id = rel.get("element_id", "").split(":")[-1]
                    rel_type = rel.get("type", "未知关系")
                    start_id = rel.get("start_node")
                    end_id = rel.get("end_node")

                    start_name = node_map.get(
                        start_id,
                        f"未知起点_{start_id[-4:]}" if start_id else "完全未知起点",
                    )
                    end_name = node_map.get(
                        end_id, f"未知终点_{end_id[-4:]}" if end_id else "完全未知终点"
                    )
                    rel_signature = f"{start_id}-{rel_type}->{end_id}"

                    if rel_signature not in seen_relationships:
                        sentences.append(f"{start_name} --[{rel_type}]--> {end_name}")
                        seen_relationships.add(rel_signature)

                connected_nodes = set()
                for rel in raw_rels:
                    connected_nodes.update([rel.get("start_node"), rel.get("end_node")])

                for node in raw_nodes:
                    node_id = node.get("element_id")
                    if node_id and node_id not in connected_nodes:
                        node_name = node_map.get(node_id, f"未命名节点_{node_id[-4:]}")
                        sentences.append(f"{node_name} ⚠️(未连接到主路径)")

                all_sentences.extend(sentences)

        except Exception as e:
            logger.error(f"路径解析异常: {str(e)}", exc_info=True)
            return ["路径解析失败，请检查数据格式"]

        return all_sentences

    def get_relationships(self) -> str:
        cypher = "CALL db.relationshipTypes()"
        relationships_raw_result = self.execute_cypher(cypher)
        relationships_cleaned = [
            item["relationshipType"].strip()
            for item in relationships_raw_result
            if "relationshipType" in item and item["relationshipType"]
        ]
        relationships_result = ", ".join(relationships_cleaned)
        return relationships_result

    @staticmethod
    def update_schema_messages(messages, relationships_str):
        for message in messages:
            if message["role"] == "system":
                message["content"] = message["content"].replace(
                    "需要的关系类型从如下关系中挑选：",
                    f"需要的关系类型从如下关系中挑选：{relationships_str}",
                )

        return messages
