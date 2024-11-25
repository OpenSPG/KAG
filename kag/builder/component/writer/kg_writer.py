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
import os
from enum import Enum
from typing import Type, Dict, List

from kag.schema.client import CHUNK_TYPE, SchemaClient, ProjectClient
from kag.builder.model.sub_graph import SubGraph, Edge, Node
from kag.builder.component.base import SinkWriter
from kag.common.base.runnable import Input, Output
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.common.vectorizer.vectorizer import Vectorizer
from kag.common.semantic_infer import SemanticEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed

from kag.schema.model.base import SpgTypeEnum

logger = logging.getLogger(__name__)


class AlterOperationEnum(str, Enum):
    Upsert = "UPSERT"
    Delete = "DELETE"


class KGWriter(SinkWriter):
    """
    A class that extends `SinkWriter` to handle writing data into a Neo4j knowledge graph.

    This class is responsible for configuring the graph store based on environment variables and
    an optional project ID, initializing the Neo4j client, and setting up the schema.
    It also manages semantic indexing and multi-threaded operations.
    """

    def __init__(self, project_id: str = None, num_threads: int = 1):
        super().__init__()
        graph_store_config = eval(os.getenv("KAG_GRAPH_STORE"))
        with_server = eval(os.getenv("KAG_PROJECT_WITH_SERVER", "False"))
        if with_server:
            project_id = int(os.getenv("KAG_PROJECT_ID") or project_id)
            client = ProjectClient()
            project = client.get_by_project_id(project_id)
            config = project.config
            config = json.loads(config) if config else {}
            graph_store_config.update(config.get("graph_store", {}))

        self.with_sim_edge = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_SIM_EDGE", "True"))
        logger.info(f"add_sim_edges = {self.with_sim_edge}")
        # Whether to constrain the node type when recalling nodes
        self.with_fix_onto = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_FIX_ONTO", "True"))
        logger.info(f"constrain similar edge under same node types = {self.with_fix_onto}")
        self.with_hyper_expand = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_HYPER_EXPAND", "True"))
        self.graph_store = Neo4jClient(**graph_store_config)
        self.graph_store.vectorizer = Vectorizer.from_config(
            eval(os.getenv("KAG_VECTORIZER"))
        )

        schema_types = SchemaClient().load()
        self.graph_store.initialize_schema(schema_types)
        self.num_threads = int(num_threads)

        self.type_mappings = {k: v.spg_type_enum for k, v in schema_types.items()}

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return None

    def add_similarity_relationship(self, node: Node, text_key=None, similarity=0.8):
        """
        Adds similarity relationships to the given node based on a threshold.

        Args:
            node (Node): The node object to which similarity relationships are added.
            text_key (str): The node's attribute for similarity calculation
            similarity (float): The similarity threshold for creating relationships.

        Returns:
            None
        """
        if (
            node.label == CHUNK_TYPE
            or self.type_mappings.get(node.label, "") == SpgTypeEnum.Concept
        ):
            return

        text_key = text_key or 'desc'
        valid_types = self.type_mappings.keys()
        target_label = node.label if (self.with_fix_onto and node.label in valid_types) else 'Entity'
        recall_nodes = self.graph_store.vector_search(
            label=target_label,
            property_key=text_key,
            query_text_or_vector=node.properties.get("desc", ""),
        )
        for recall_node in recall_nodes:
            if (
                recall_node["node"]["id"] == node.id
                or recall_node["score"] < similarity
            ):
                continue
            recall_label = recall_node["node"]["semanticType"]
            recall_label = recall_label if recall_label in valid_types else 'Entity'
            self.graph_store.upsert_relationship(
                start_node_label=node.label,
                start_node_id_value=node.id,
                end_node_label=recall_label,
                end_node_id_value=recall_node["node"]["id"],
                rel_type="similarity",
                properties={"score": recall_node["score"]},
                upsert_nodes=False,
            )

    def upsert_node(self, node: Node):
        """
        Upserts a node into the graph store.

        Args:
            node (Node): The node object to be upserted.

        Returns:
            None
        """
        if not node.id or not node.name:
            return
        valid_types = self.type_mappings.keys()
        node.label = node.label if node.label in valid_types else 'Entity'
        properties = {"id": node.id, "name": node.name}
        properties.update(node.properties)

        self.graph_store.upsert_node(label=node.label, properties=properties)

        if self.with_sim_edge:
            if node.label == SemanticEnhance.concept_label:
                self.add_similarity_relationship(
                    node, text_key="name", similarity=float(os.getenv("KAG_INDEXER_CONCEPT_SIM_THRESHOLD"))
                )
            else:
                self.add_similarity_relationship(
                    node, text_key="desc", similarity=float(os.getenv("KAG_INDEXER_SIMILARITY_THRESHOLD"))
                )

    def upsert_edge(self, edge: Edge):
        """
        Upserts an edge into the graph store.

        Args:
            edge (Edge): The edge object to be upserted.

        Returns:
            None
        """
        if not edge.from_id or not edge.to_id:
            return
        valid_types = self.type_mappings.keys()
        edge.from_type = edge.from_type if edge.from_type in valid_types else 'Entity'
        edge.to_type = edge.to_type if edge.to_type in valid_types else 'Entity'
        self.graph_store.upsert_relationship(
            start_node_label=edge.from_type,
            start_node_id_value=edge.from_id,
            end_node_label=edge.to_type,
            end_node_id_value=edge.to_id,
            rel_type=edge.label,
            properties=edge.properties,
            upsert_nodes=False,
        )

    def batch_vectorize(self, input: SubGraph):
        """
        Batch vectorizes nodes within a subgraph.

        Args:
            input (SubGraph): The subgraph containing nodes to be vectorized.

        Returns:
            None
        """
        node_list = []
        node_batch = []
        for node in input.nodes:
            if not node.id or not node.name:
                continue
            properties = {"id": str(node.id), "name": str(node.name)}
            properties.update({k: v for k, v in node.properties.items() if k not in ['id', 'name']})            
            properties.update(node.properties)
            node_list.append((node, properties))
            node_batch.append((node.label, properties.copy()))
        self.graph_store.batch_preprocess_node_properties(node_batch)
        for (node, properties), (_node_label, new_properties) in zip(
            node_list, node_batch
        ):
            for key, value in properties.items():
                if key in new_properties and new_properties[key] == value:
                    del new_properties[key]
            node.properties.update(new_properties)

    def upsert(self, input: SubGraph):
        """
        Upserts nodes and edges into the graph store.

        Args:
            input (SubGraph): The subgraph containing nodes and edges to be upserted.

        Returns:
            None
        """
        self.batch_vectorize(input)

        with ThreadPoolExecutor(self.num_threads) as node_executor:
            node_futures = [
                node_executor.submit(self.upsert_node, node) for node in input.nodes
            ]
        while node_futures:
            for future in as_completed(node_futures):
                node_futures.remove(future)

        with ThreadPoolExecutor(self.num_threads) as edge_executor:
            edge_futures = [
                edge_executor.submit(self.upsert_edge, edge) for edge in input.edges
            ]
        while edge_futures:
            for future in as_completed(edge_futures):
                edge_futures.remove(future)

    def delete(self, input: SubGraph):
        """
        Deletes nodes and edges from the graph store.

        Args:
            input (SubGraph): The subgraph containing nodes and edges to be deleted.

        Returns:
            None
        """
        for node in input.nodes:
            self.graph_store.delete_node(label=node.label, id_value=node.id)
        for edge in input.edges:
            self.graph_store.delete_relationship(
                start_node_label=edge.from_type,
                start_node_id_value=edge.from_id,
                end_node_label=edge.to_type,
                end_node_id_value=edge.to_id,
                rel_type=edge.label,
            )

    def invoke(
        self, input: Input, alter_operation: str = AlterOperationEnum.Upsert
    ) -> List[Output]:
        """
        Invokes the specified operation (upsert or delete) on the graph store.

        Args:
            input (Input): The input object representing the subgraph to operate on.
            alter_operation (str): The type of operation to perform (Upsert or Delete).

        Returns:
            List[Output]: A list of output objects (currently always [None]).
        """

        retry_times = 0
        while retry_times < 3:
            try:
                if alter_operation == AlterOperationEnum.Upsert:
                    self.upsert(input)
                elif alter_operation == AlterOperationEnum.Delete:
                    self.delete(input)
                return [None]
            except Exception as e:
                import traceback

                traceback.print_exc()
                logger.info(e)
                retry_times += 1
                logger.info(f"Retry {retry_times} times")
        return [None]

    def _handle(self, input: Dict, alter_operation: str, **kwargs):
        """The calling interface provided for SPGServer."""
        _input = self.input_types.from_dict(input)
        _output = self.invoke(_input, alter_operation)
        return None
