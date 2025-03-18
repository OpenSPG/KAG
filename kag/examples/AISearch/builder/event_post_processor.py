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
import logging
from typing import List
from tenacity import stop_after_attempt, retry
from kag.interface import PostProcessorABC
from kag.interface import ExternalGraphLoaderABC
from kag.builder.model.sub_graph import SubGraph
from kag.common.conf import KAGConstants, KAG_PROJECT_CONF
from kag.common.utils import get_vector_field_name
from knext.search.client import SearchClient
from knext.schema.client import SchemaClient, OTHER_TYPE
import json

from datetime import datetime, timezone, timedelta
import collections
logger = logging.getLogger(__name__)

chunk_fields = [
    "nameEmbed",
    "descEmbed",
    "position",
    "updateTime",
    "updateTimeStamp",
    "publishTime",
    "publishTimeStamp",
    "createTime",
    "createTimeStamp",
]
event_fields = [
    "embedding",
    "pName",
    "subName",
    "subId",
    "updateTime",
    "updateTimeStamp",
]
entity_fields = ["nameEmbed", "updateTime", "updateTimeStamp", "entityType"]

project_name = "XB."
@PostProcessorABC.register("base", as_default=True)
@PostProcessorABC.register("event_post_processor")
class EventPostProcessor(PostProcessorABC):
    """
    A class that extends the PostProcessorABC base class.
    It provides methods to handle various post-processing tasks on subgraphs
    including filtering, entity linking based on similarity, and linking based on an external graph.
    """

    def __init__(
            self,
            similarity_threshold: float = 0.9,
            external_graph: ExternalGraphLoaderABC = None,
    ):
        """
        Initializes the KAGPostProcessor instance.

        Args:
            similarity_threshold (float, optional): The similarity threshold for entity linking. Defaults to 0.9.
            external_graph (ExternalGraphLoaderABC, optional): An instance of ExternalGraphLoaderABC for external graph-based linking. Defaults to None.
        """
        super().__init__()
        self.schema = SchemaClient(project_id=KAG_PROJECT_CONF.project_id).load()
        self.similarity_threshold = similarity_threshold
        self.external_graph = external_graph
        self._init_search()

    def format_label(self, label: str):
        """
        Formats the label by adding the project namespace if it is not already present.

        Args:
            label (str): The label to be formatted.

        Returns:
            str: The formatted label.
        """
        namespace = KAG_PROJECT_CONF.namespace
        if label.split(".")[0] == namespace:
            return label
        return f"{namespace}.{label}"

    def _init_search(self):
        """
        Initializes the search client for entity linking.
        """
        self._search_client = SearchClient(
            KAG_PROJECT_CONF.host_addr, KAG_PROJECT_CONF.project_id
        )

    def filter_invalid_data(self, graph: SubGraph):
        """
        Filters out invalid nodes and edges from the subgraph.

        Args:
            graph (SubGraph): The subgraph to be filtered.

        Returns:
            SubGraph: The filtered subgraph.
        """
        valid_nodes = []
        valid_edges = []
        for node in graph.nodes:
            if not node.id or not node.label:
                continue
            if node.label not in self.schema:
                node.label = self.format_label(OTHER_TYPE)
            # for k in node.properties.keys():
            #     if k not in self.schema[node.label]:
            #         continue
            valid_nodes.append(node)
        for edge in graph.edges:
            if edge.label:
                valid_edges.append(edge)
        return SubGraph(nodes=valid_nodes, edges=valid_edges)

    @retry(stop=stop_after_attempt(3))
    def _entity_link(
            self, graph: SubGraph, property_key: str = "name", labels: List[str] = None
    ):
        """
        Performs entity linking based on the given property key and labels.

        Args:
            graph (SubGraph): The subgraph to perform entity linking on.
            property_key (str, optional): The property key to use for linking. Defaults to "name".
            labels (List[str], optional): The labels to consider for linking. Defaults to None.
        """
        vector_field_name = get_vector_field_name(property_key)
        for node in graph.nodes:
            if labels is None:
                link_labels = [self.format_label(node.label)]
            else:
                link_labels = [self.format_label(x) for x in labels]
            vector = node.properties.get(vector_field_name)
            if vector:
                all_similar_nodes = []
                for label in link_labels:
                    similar_nodes = self._search_client.search_vector(
                        label=label,
                        property_key=property_key,
                        query_vector=[float(x) for x in vector],
                        topk=1,
                        params={},
                    )
                    all_similar_nodes.extend(similar_nodes)
                for item in all_similar_nodes:
                    score = item["score"]
                    if (
                            score >= self.similarity_threshold
                            and node.id != item["node"]["id"]
                    ):
                        graph.add_edge(
                            node.id,
                            node.label,
                            KAGConstants.KAG_SIMILAR_EDGE_NAME,
                            item["node"]["id"],
                            item["node"]["__labels__"][0],
                        )

    def similarity_based_link(self, graph: SubGraph, property_key: str = "name"):
        """
        Performs entity linking based on similarity.

        Args:
            graph (SubGraph): The subgraph to perform entity linking on.
            property_key (str, optional): The property key to use for linking. Defaults to "name".
        """
        self._entity_link(graph, property_key, None)

    def external_graph_based_link(self, graph: SubGraph, property_key: str = "name"):
        """
        Performs entity linking based on the user provided external graph.

        Args:
            graph (SubGraph): The subgraph to perform entity linking on.
            property_key (str, optional): The property key to use for linking. Defaults to "name".
        """
        if not self.external_graph:
            return
        labels = self.external_graph.get_allowed_labels()
        self._entity_link(graph, property_key, labels)

    def _invoke(self, input, **kwargs):
        """
        Invokes the post-processing pipeline on the input subgraph.

        Args:
            input: The input subgraph to be processed.

        Returns:
            List[SubGraph]: A list containing the processed subgraph.
        """
        '''
        origin_num_nodes = len(input.nodes)
        origin_num_edges = len(input.edges)
        new_graph = self.filter_invalid_data(input)
        self.similarity_based_link(new_graph)
        self.external_graph_based_link(new_graph)
        new_num_nodes = len(new_graph.nodes)
        new_num_edges = len(new_graph.edges)
        logger.debug(
            f"origin: {origin_num_nodes}/{origin_num_edges}, processed: {new_num_nodes}/{new_num_edges}"
        )'''
        new_graph = self.process_to_log(input)
        return [new_graph]


    def process_to_log(self, res_total):
        chunk_node = []
        for node in res_total.nodes:
            if node.label == "Chunk":
                chunk_node.append(node)
        edge_total = SubGraph(nodes = [],edges = [])
        if len(chunk_node) > 0:
            sorted_chunk_node = sorted(
                chunk_node,
                key=lambda x: (
                    x.properties["position"]
                    if "position" in x.properties
                    else 0
                ),
            )
            for idx, node in enumerate(sorted_chunk_node):
                if idx + 1 >= len(sorted_chunk_node):
                    break
                edge_total.add_edge(
                    node.id,
                    node.label,
                    "beforeChunk",
                    sorted_chunk_node[idx + 1].id,
                    sorted_chunk_node[idx + 1].label,
                )
                edge_total.add_edge(
                    node.id,
                    node.label,
                    "sourceDoc",
                    "doc_id",
                    "DOC",
                )

        # for r2 in res2:
        #     res_total.merge(r2)
        res_total.merge(edge_total)

        def remove_dup_node(res):
            # Create a set to track unique (id, label) combinations
            seen = set()
            unique_nodes = []

            # Keep only unique nodes
            for node in res.nodes:
                node_key = (node.id, node.label)
                if node_key not in seen:
                    seen.add(node_key)
                    unique_nodes.append(node)

            # Replace the nodes list with unique nodes
            res.nodes = unique_nodes

            return res

        res_total = remove_dup_node(res_total)
        res_total = res_total.to_dict()

        res_total_no_vector = self.remove_vector_fields(res_total)
        # put_logs_for_eval(
        #     res_total_no_vector,
        #     target_project,
        #     target_logstore_eval,
        # )


        self.process_content(res_total, "doc_pub_time", "doc_pub_timestamp")

        docs, base_info, miss_edges, miss_nodes, error_nodes, extra_nodes = (
            self.check_valid(res_total)
        )

        error_log = {
            "doc_id": "doc_id",
            "error_nodes": error_nodes,
            "extra_nodes": extra_nodes,
            "miss_edges": miss_edges,
            "miss_nodes": miss_nodes,
        }
        # put_logs_for_error(error_log, target_project, target_logstore_error)

        # Remove error nodes
        error_node_ids = {
            node["id"] for nodes in error_nodes.values() for node in nodes
        }
        res_total["resultNodes"] = [
            node
            for node in res_total["resultNodes"]
            if node["id"] not in error_node_ids
        ]

        # Remove extra nodes
        extra_node_ids = {
            node["id"] for nodes in extra_nodes.values() for node in nodes
        }
        res_total["resultNodes"] = [
            node
            for node in res_total["resultNodes"]
            if node["id"] not in extra_node_ids
        ]
        return SubGraph.from_dict(res_total)



    def remove_vector_fields(self, data_dict):
        """
        移除数据中的向量字段，返回无向量的新字典
        """
        # 创建深拷贝以避免修改原始数据
        import copy

        result = copy.deepcopy(data_dict)

        # 需要移除的向量字段后缀
        vector_suffixes = ["_name_vector", "_content_vector", "_desc_vector", "_p_name_vector"]

        # 处理节点
        if "resultNodes" in result:
            for node in result["resultNodes"]:
                if "properties" in node:
                    # 找出所有需要删除的键
                    keys_to_delete = [
                        key
                        for key in node["properties"].keys()
                        if any(key.endswith(suffix) for suffix in vector_suffixes)
                    ]
                    # 删除这些键
                    for key in keys_to_delete:
                        del node["properties"][key]

        return result


    def process_content(self, content, doc_pub_time, doc_pub_timestamp):
        resultNodes = content["resultNodes"]
        resultEdges = content["resultEdges"]
        for node in resultNodes:
            properties = node["properties"]
            if node["label"] == "Event":
                node["label"] = project_name + "Event"
            elif node["label"] == "Document":
                node["properties"]["description"] = properties.pop("desc")
                node["properties"]["isDel"] = 0
                node["label"] = project_name + "Document"
            elif node["label"] == "Chunk":
                node["label"] = project_name + "Chunk"
                node["properties"]["description"] = properties.pop("content")
            else:
                node["label"] = project_name + "Entity"

            if "_name_vector" in properties:
                if node["label"] == project_name + "Event":
                    properties["embedding"] = properties.pop("_name_vector")
                else:
                    properties["nameEmbed"] = properties.pop("_name_vector")
            if "_content_vector" in properties:
                properties["descEmbed"] = properties.pop("_content_vector")
            if "_desc_vector" in properties:
                properties["descEmbed"] = properties.pop("_desc_vector")
            if ("_p_name_vector") in properties:
                properties["pNameEmbed"] = properties.pop("_p_name_vector")
            if "semanticType" in node:
                node["entityType"] = node.pop("semanticType")

        for edge in resultEdges:
            edge["fromType"] = project_name + edge["fromType"]
            edge["toType"] = project_name + edge["toType"]

        for node in resultNodes:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            time_str = self.get_china_time()
            node["updateTime"] = time_str
            node["createTime"] = time_str
            node["updateTimeStamp"] = timestamp
            node["createTimeStamp"] = timestamp

            if node["label"] == (project_name + "Chunk") or node["label"] == (project_name + "Document"):
                node["properties"]["publishTime"] = time_str
                node["properties"]["publishTimeStamp"] = timestamp
            for k, v in node.items():
                if k != "id" and k != "name" and k != "label" and k != "properties":
                    node["properties"][k] = v

    def get_china_time(self):
        current_time = datetime.now(timezone.utc)
        china_timezone = timezone(timedelta(hours=8))
        china_time = current_time.astimezone(china_timezone)
        formatted_china_time = china_time.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_china_time

    def check_valid(self, data):
        def node_format(node):
            return {"id": node["id"], "name": node["name"], "label": node["label"]}

        node_map = collections.defaultdict(lambda: {})
        edge_map = {}
        base_info = collections.defaultdict(lambda: 0)
        for node in data["resultNodes"]:
            node_map[node["label"]][node["id"]] = node
            base_info["total_node"] += 1
            base_info[f"node->{node['label']}"] += 1
        edges = data["resultEdges"]
        for edge in edges:
            e_id = f"{edge['from']}_{edge['fromType']}_{edge['label']}_{edge['to']}_{edge['toType']}"
            edge_map[e_id] = edges
            base_info["total_edge"] += 1
            base_info[f"edge->{edge['fromType']}_{edge['label']}_{edge['toType']}"] += 1

        miss_edges, error_nodes = collections.defaultdict(
            lambda: list()
        ), collections.defaultdict(lambda: list())
        miss_nodes = collections.defaultdict(lambda: list())
        extra_nodes = collections.defaultdict(lambda: list())  # 多余的结点
        docs, chunks, events, entitys = (
            node_map["Document"],
            node_map["Chunk"],
            node_map.get("Event", {}),
            node_map.get("Entity", {}),
        )

        # 检查点是否满足要求
        for _, chunk in chunks.items():
            if not chunk["name"]:
                error_nodes["chunk->name"].append(node_format(chunk))
            for field in chunk_fields:
                field_value = chunk["properties"].get(field, "")
                if field_value ==  "" or field_value is None:
                    error_nodes[f"chunk->{field}"].append(node_format(chunk))

        all_edge_exist_entity_ids = set()
        for _, event in events.items():
            if not event["name"]:
                error_nodes["event->name"].append(node_format(event))
            for field in event_fields:
                field_value = event["properties"].get(field, "")
                if not field_value:
                    error_nodes[f"event->{field}"].append(node_format(event))
            # 特殊的规则
            if event["properties"].get("objName", "") and not event["properties"].get(
                    "objId", ""
            ):
                error_nodes[f"event->objId"].append(node_format(event))
            if not event["properties"].get("objName", "") and event["properties"].get(
                    "objId", ""
            ):
                error_nodes[f"event->objName"].append(node_format(event))

            if event["properties"].get("objId", ""):
                all_edge_exist_entity_ids.add(event["properties"]["objId"])
            if event["properties"].get("subId", ""):
                all_edge_exist_entity_ids.add(event["properties"]["subId"])

        for _, entity in entitys.items():
            if not entity["name"]:
                error_nodes["entity->name"].append(node_format(entity))

            for field in entity_fields:
                field_value = entity["properties"].get(field, "")
                if not field_value:
                    error_nodes[f"entity->{field}"].append(node_format(entity))
            # 判断结点是一个孤立点
            if entity["id"] not in all_edge_exist_entity_ids:
                extra_nodes["entity"].append(node_format(entity))

        # # 检查chunk出发的关系
        # chunk_by_pos = {}
        # for _, chunk in chunks.items():
        #     chunk_by_pos[int(chunk["properties"]["position"])] = chunk

        for _, chunk in chunks.items():
            # 检查到doc的关系
            for _, doc in docs.items():
                key = f"{chunk['id']}_{chunk['label']}_sourceDoc_{doc['id']}_{doc['label']}"
                if key not in edge_map:
                    miss_edges["chunk->sourceDoc"].append(key)
            # # 检查before chunk关系
            # pos = int(chunk["properties"]["position"])
            # if pos + 1 in chunk_by_pos:
            #     # 表示有before chunk的
            #     after_chunk = chunk_by_pos[pos + 1]
            #     key = f"{chunk['id']}_{chunk['label']}_beforeChunk_{after_chunk['id']}_{after_chunk['label']}"
            #     if key not in edge_map:
            #         miss_edges["beforeChunk"].append(key)

        for _, event in events.items():
            # 事件到doc
            for _, doc in docs.items():
                key = f"{event['id']}_{event['label']}_sourceDoc_{doc['id']}_{doc['label']}"
                if key not in edge_map:
                    miss_edges["event->sourceDoc"].append(key)
            # 事件到chunk
            for _, chunk in chunks.items():
                key = f"{event['id']}_{event['label']}_sourceChunk_{chunk['id']}_{chunk['label']}"
                if key not in edge_map:
                    miss_edges["event->sourceChunk"].append(key)
            # 事件到实体
            for _, entity in entitys.items():
                if (
                        "subId" not in entity["properties"]
                        and "objId" not in entity["properties"]
                ):
                    continue
                # 不存在的点 和 边
                if "subId" in entity["properties"]:
                    key = f"{event['id']}_{event['label']}_subId_{entity['properties']['subId']}_Entity"
                    if key not in edge_map:
                        miss_edges["event->subId"].append(key)
                    if entity["properties"]["subId"] not in entity:
                        miss_nodes["entity"].append(entity["properties"]["subId"])
                if "objId" in entity["properties"]:
                    key = f"{event['id']}_{event['label']}_objId_{entity['properties']['objId']}_Entity"
                    if key not in edge_map:
                        miss_edges["event->objId"].append(key)
                    if entity["properties"]["objId"] not in entity:
                        miss_nodes["entity"].append(entity["properties"]["objId"])

        for _, entity in entitys.items():
            for _, doc in docs.items():
                key = f"{entity['id']}_{entity['label']}_sourceDoc_{doc['id']}_{doc['label']}"
                if key not in edge_map:
                    miss_edges["entity->sourceDoc"].append(key)
            # 事件到chunk
            for _, chunk in chunks.items():
                key = f"{entity['id']}_{entity['label']}_sourceChunk_{chunk['id']}_{chunk['label']}"
                if key not in edge_map:
                    miss_edges["entity->sourceChunk"].append(key)

        miss_edge_num = {_type: len(mynode) for _type, mynode in miss_edges.items()}
        miss_nodes_num = {_type: len(mynode) for _type, mynode in miss_nodes.items()}
        error_nodes_num = {_type: len(mynode) for _type, mynode in error_nodes.items()}
        print(f"base info {json.dumps(base_info, ensure_ascii=False)}")
        print(f"miss edge {json.dumps(miss_edge_num, ensure_ascii=False)}")
        print(f"miss node {json.dumps(miss_nodes_num, ensure_ascii=False)}")
        print(f"error node {json.dumps(error_nodes_num, ensure_ascii=False)}")

        return docs, base_info, miss_edges, miss_nodes, error_nodes, extra_nodes