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
import os
from kag.interface import PostProcessorABC, VectorizerABC
from kag.builder.model.sub_graph import Node, Edge, SubGraph
from kag.common.conf import KAG_CONFIG

pwd = os.path.dirname(__file__)


def get_config():
    config = {
        "type": "base",
        "similarity_threshold": 0.1,
    }
    return config


def create_mock_graph():
    nodes = [
        Node("Apple", name="Apple", label="Concept", properties={}),
        Node("Banana", name="Banana", label="Concept", properties={}),
        Node("Peach", name="Peach", label="Concept", properties={}),
        Node("000", name="000", label="Number", properties={}),
        Node("Error", name="Peach", label="", properties={}),
    ]

    edges = [
        Edge("1", from_node=nodes[0], to_node=nodes[1], label="sim", properties={}),
        Edge("2", from_node=nodes[0], to_node=nodes[2], label="sim", properties={}),
        Edge("3", from_node=nodes[1], to_node=nodes[2], label="sim", properties={}),
        Edge("4", from_node=nodes[0], to_node=nodes[3], label="", properties={}),
        Edge("5", from_node=nodes[0], to_node=nodes[4], label="", properties={}),
    ]
    graph = SubGraph(nodes=nodes, edges=edges)
    return graph


def test_postprocessor_filter():
    config = get_config()
    postprocessor = PostProcessorABC.from_config(config)
    graph = create_mock_graph()
    new_graph = postprocessor.filter_invalid_data(graph)
    assert len(new_graph.nodes) == 3
    assert len(new_graph.edges) == 3
    for node in new_graph.nodes:
        assert node.label == "Concept"
    for edge in new_graph.edges:
        assert edge.label == "sim"


def test_postprocessor_add_sim_edges():
    config = get_config()
    postprocessor = PostProcessorABC.from_config(config)
    graph = create_mock_graph()
    vectorizer = VectorizerABC.from_config(KAG_CONFIG.all_config["vectorizer"])
    graph = vectorizer.invoke(graph)[0]
    origin_num_edges = len(graph.edges)
    postprocessor.similarity_based_link(graph)
    assert len(graph.edges) > origin_num_edges


def test_postprocessor_add_eg_edges():
    config = get_config()
    config["external_graph"] = {
        "type": "base",
        "node_file_path": os.path.join(pwd, "../data/nodes.json"),
        "edge_file_path": os.path.join(pwd, "../data/edges.json"),
        "match_config": {
            "k": 1,
            "threshold": 0.9,
        },
    }
    postprocessor = PostProcessorABC.from_config(config)
    graph = create_mock_graph()
    vectorizer = VectorizerABC.from_config(KAG_CONFIG.all_config["vectorizer"])
    graph = vectorizer.invoke(graph)[0]
    origin_num_edges = len(graph.edges)
    postprocessor.external_graph_based_link(graph)
    assert len(graph.edges) > origin_num_edges
