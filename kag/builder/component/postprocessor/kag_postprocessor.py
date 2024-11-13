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
from typing import List
from kag.interface import PostProcessorABC
from kag.interface import ExternalGraphLoaderABC
from kag.builder.model.sub_graph import SubGraph
from kag.common.conf import KAGConstants, KAG_PROJECT_CONF
from kag.common.utils import get_vector_field_name
from knext.search.client import SearchClient
from knext.schema.client import SchemaClient


@PostProcessorABC.register("base", as_default=True)
class KAGPostProcessor(PostProcessorABC):
    def __init__(
        self,
        similarity_threshold: float = 0.9,
        external_graph: ExternalGraphLoaderABC = None,
    ):
        self.schema = SchemaClient(project_id=KAG_PROJECT_CONF.project_id).load()
        self.similarity_threshold = similarity_threshold
        self.external_graph = external_graph
        self._init_search()

    def format_label(self, label: str):
        namespace = KAG_PROJECT_CONF.namespace
        if label.startswith(namespace):
            return label
        return f"{namespace}.{label}"

    def _init_search(self):
        self._search_client = SearchClient(
            KAG_PROJECT_CONF.host_addr, KAG_PROJECT_CONF.project_id
        )

    def filter_invalid_data(self, graph: SubGraph):
        valid_nodes = []
        valid_edges = []
        for node in graph.nodes:
            if not node.id or not node.label:
                continue
            if node.label not in self.schema:
                continue
            # for k in node.properties.keys():
            #     if k not in self.schema[node.label]:
            #         continue
            valid_nodes.append(node)
        for edge in graph.edges:
            if edge.label:
                valid_edges.append(edge)
        return SubGraph(nodes=valid_nodes, edges=valid_edges)

    def _entity_link(
        self, graph: SubGraph, property_key: str = "name", labels: List[str] = None
    ):
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
                        query_vector=vector,
                        topk=1,
                    )
                    all_similar_nodes.extend(similar_nodes)
                for item in all_similar_nodes:
                    score = item["score"]
                    if score >= self.similarity_threshold:
                        graph.add_edge(
                            node.id,
                            node.label,
                            KAGConstants.KAG_SIMILAR_EDGE_NAME,
                            item["node"]["id"],
                            item["node"]["__labels__"][0],
                        )

    def similarity_based_link(self, graph: SubGraph, property_key: str = "name"):
        self._entity_link(graph, property_key, None)

    def external_graph_based_link(self, graph: SubGraph, property_key: str = "name"):
        if not self.external_graph:
            return
        labels = self.external_graph.get_allowed_labels()
        self._entity_link(graph, property_key, labels)

    def invoke(self, input):
        new_graph = self.filter_invalid_data(input)
        self.similarity_based_link(new_graph)
        self.external_graph_based_link(new_graph)
        return [new_graph]
