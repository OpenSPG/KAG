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
from kag.common.conf import KAGConstants
from kag.common.utils import get_vector_field_name
from knext.search.client import SearchClient
from knext.schema.client import SchemaClient, OTHER_TYPE


logger = logging.getLogger()


@PostProcessorABC.register("base", as_default=True)
@PostProcessorABC.register("kag_post_processor")
class KAGPostProcessor(PostProcessorABC):
    """
    A class that extends the PostProcessorABC base class.
    It provides methods to handle various post-processing tasks on subgraphs
    including filtering, entity linking based on similarity, and linking based on an external graph.
    """

    def __init__(
        self,
        similarity_threshold: float = None,
        external_graph: ExternalGraphLoaderABC = None,
        **kwargs,
    ):
        """
        Initializes the KAGPostProcessor instance.

        Args:
            similarity_threshold (float, optional): The similarity threshold for entity linking. Defaults to 0.9.
            external_graph (ExternalGraphLoaderABC, optional): An instance of ExternalGraphLoaderABC for external graph-based linking. Defaults to None.
        """
        super().__init__(**kwargs)
        self.schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
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
        namespace = self.kag_project_config.namespace
        if label.split(".")[0] == namespace:
            return label
        return f"{namespace}.{label}"

    def _init_search(self):
        """
        Initializes the search client for entity linking.
        """
        self._search_client = SearchClient(
            self.kag_project_config.host_addr, self.kag_project_config.project_id
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

    @retry(stop=stop_after_attempt(3), reraise=True)
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
        origin_num_nodes = len(input.nodes)
        origin_num_edges = len(input.edges)
        new_graph = self.filter_invalid_data(input)
        if self.similarity_threshold is not None:
            self.similarity_based_link(new_graph)
            self.external_graph_based_link(new_graph)
        new_num_nodes = len(new_graph.nodes)
        new_num_edges = len(new_graph.edges)
        logger.debug(
            f"origin: {origin_num_nodes}/{origin_num_edges}, processed: {new_num_nodes}/{new_num_edges}"
        )
        return [new_graph]
