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
import numpy as np
import logging
from typing import List, Union, Dict
from kag.interface import ExternalGraphLoaderABC, MatchConfig
from kag.builder.model.sub_graph import Node, Edge, SubGraph
from knext.schema.client import SchemaClient

from knext.search.client import SearchClient


logger = logging.getLogger()


@ExternalGraphLoaderABC.register("base", constructor="from_json_file", as_default=True)
class DefaultExternalGraphLoader(ExternalGraphLoaderABC):
    """
    A default implementation of the ExternalGraphLoaderABC interface.

    This class is responsible for loading external graph data based on the provided nodes, edges, and match configuration.
    """

    def __init__(
        self, nodes: List[Node], edges: List[Edge], match_config: MatchConfig, **kwargs
    ):
        """
        Initializes the DefaultExternalGraphLoader with the given nodes, edges, and match configuration.

        Args:
            nodes (List[Node]): A list of Node objects representing the nodes in the graph.
            edges (List[Edge]): A list of Edge objects representing the edges in the graph.
            match_config (MatchConfig): The configuration for matching query str to graph nodes.
        """
        super().__init__(match_config, **kwargs)
        self.schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
        for node in nodes:
            if node.label not in self.schema:
                raise ValueError(
                    f"Type of node {node.to_dict()} is beyond the schema definition."
                )
            for k in node.properties.keys():
                if k not in self.schema[node.label]:
                    raise ValueError(
                        f"Property of node {node.to_dict()} is beyond the schema definition."
                    )
        self.nodes = nodes
        self.edges = edges

        self.vocabulary = {}
        self.node_labels = set()
        for node in self.nodes:
            self.vocabulary[node.name] = node
            self.node_labels.add(node.label)

        import jieba

        for word in self.vocabulary.keys():
            jieba.add_word(word)

        self.match_config = match_config
        self._init_search()

    def _init_search(self):
        self._search_client = SearchClient(
            self.kag_project_config.host_addr, self.kag_project_config.project_id
        )

    def _group_by_label(self, data: Union[List[Node], List[Edge]]):
        groups = {}

        for item in data:
            label = item.label
            if label not in groups:
                groups[label] = [item]
            else:
                groups[label].append(item)
        return list(groups.values())

    def _group_by_cnt(self, data, n):
        return [data[i : i + n] for i in range(0, len(data), n)]

    def dump(self, max_num_nodes: int = 4096, max_num_edges: int = 4096):
        graphs = []
        # process nodes
        for item in self._group_by_label(self.nodes):
            for grouped_nodes in self._group_by_cnt(item, max_num_nodes):
                graphs.append(SubGraph(nodes=grouped_nodes, edges=[]))

        # process edges
        for item in self._group_by_label(self.edges):
            for grouped_edges in self._group_by_cnt(item, max_num_edges):
                graphs.append(SubGraph(nodes=[], edges=grouped_edges))

        return graphs

    def ner(self, content: str):
        output = []
        import jieba

        for word in jieba.cut(content):
            if word in self.vocabulary:
                output.append(self.vocabulary[word])
        return output

    def get_allowed_labels(self, labels: List[str] = None):
        allowed_labels = []

        namespace = self.kag_project_config.namespace
        if labels is None:
            allowed_labels = [f"{namespace}.{x}" for x in self.node_labels]
        else:
            for label in labels:
                # remove namespace
                if label.startswith(self.kag_project_config.namespace):
                    label = label.split(".")[1]
                if label in self.node_labels:
                    allowed_labels.append(f"{namespace}.{label}")
        return allowed_labels

    def search_result_to_node(self, search_result: Dict):
        output = []
        for label in search_result["__labels__"]:
            node = {
                "id": search_result["id"],
                "name": search_result["name"],
                "label": label,
            }
            output.append(Node.from_dict(node))
        return output

    def text_match(self, query: str, k: int = 1, labels: List[str] = None):
        allowed_labels = self.get_allowed_labels(labels)
        text_matched = self._search_client.search_text(query, allowed_labels, topk=k)
        return text_matched

    def vector_match(
        self,
        query: Union[List[float], np.ndarray],
        k: int = 1,
        threshold: float = 0.9,
        labels: List[str] = None,
    ):
        allowed_labels = self.get_allowed_labels(labels)
        if isinstance(query, np.ndarray):
            query = query.tolist()
        matched_results = []
        for label in allowed_labels:
            vector_matched = self._search_client.search_vector(
                label=label, property_key="name", query_vector=query, topk=k
            )
            matched_results.extend(vector_matched)

        filtered_results = []
        for item in matched_results:
            score = item["score"]
            if score >= threshold:
                filtered_results.append(item)
        return filtered_results

    def match_entity(self, query: Union[str, List[float], np.ndarray]):
        if isinstance(query, str):
            return self.text_match(
                query, k=self.match_config.k, labels=self.match_config.labels
            )
        else:
            return self.vector_match(
                query,
                k=self.match_config.k,
                labels=self.match_config.labels,
                threshold=self.match_config.threshold,
            )

    @classmethod
    def from_json_file(
        cls,
        node_file_path: str,
        edge_file_path: str,
        match_config: MatchConfig,
    ):
        """
        Creates an instance of DefaultExternalGraphLoader from JSON files containing node and edge data.

        Args:
            node_file_path (str): The path to the JSON file containing node data.
            edge_file_path (str): The path to the JSON file containing edge data.
            match_config (MatchConfig): The configuration for matching query str to graph nodes.

        Returns:
            DefaultExternalGraphLoader: An instance of DefaultExternalGraphLoader initialized with the data from the JSON files.
        """
        nodes = []
        for item in json.load(
            open(node_file_path, "r", encoding="utf-8", newline="\n")
        ):
            nodes.append(Node.from_dict(item))
        edges = []
        for item in json.load(
            open(edge_file_path, "r", encoding="utf-8", newline="\n")
        ):
            edges.append(Edge.from_dict(item))
        return cls(nodes=nodes, edges=edges, match_config=match_config)
