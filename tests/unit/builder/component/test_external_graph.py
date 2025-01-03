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
from kag.interface import ExternalGraphLoaderABC, SinkWriterABC, VectorizerABC
from kag.builder.model.sub_graph import Node
from kag.common.conf import KAG_CONFIG
from kag.common.utils import get_vector_field_name

pwd = os.path.dirname(__file__)


def get_config():
    config = {
        "type": "base",
        "node_file_path": os.path.join(pwd, "../data/nodes.json"),
        "edge_file_path": os.path.join(pwd, "../data/edges.json"),
        "match_config": {
            "k": 1,
            "threshold": 0.9,
        },
    }
    return config


def _test_eg_base():
    config = get_config()
    eg = ExternalGraphLoaderABC.from_config(config)
    assert len(eg.nodes) == 38
    assert len(eg.edges) == 19


def _test_eg_dump():
    config = get_config()
    eg = ExternalGraphLoaderABC.from_config(config)
    graphs = eg.invoke(None)
    for graph in graphs:
        if len(graph.nodes) > 0:
            assert len(graph.edges) == 0
            labels = set()
            for node in graph.nodes:
                labels.add(node.label)
            assert len(labels) == 1
        elif len(graph.edges) > 0:
            assert len(graph.nodes) == 0
            labels = set()
            for edge in graph.edges:
                labels.add(edge.label)
            assert len(labels) == 1

    vectorizer = VectorizerABC.from_config(KAG_CONFIG.all_config["vectorizer"])
    writer = SinkWriterABC.from_config(KAG_CONFIG.all_config["writer"])
    for graph in graphs:
        new_graph = vectorizer.invoke(graph)[0]
        writer.invoke(new_graph)


def _test_eg_query():
    config = get_config()
    eg = ExternalGraphLoaderABC.from_config(config)
    entities = eg.ner("促生长素抑制素和蛋白酶有什么关系")
    assert len(entities) > 0
    for entity in entities:
        assert isinstance(entity, Node)

    text_matched = eg.match_entity("蛋白水解酶")
    assert len(text_matched) > 0 and text_matched[0]["node"]["name"] == "蛋白水解酶"
    vector = text_matched[0]["node"][get_vector_field_name("name")]
    vector_matched = eg.match_entity(vector)
    assert len(vector_matched) > 0 and vector_matched[0]["node"]["name"] == "蛋白水解酶"


def test_eg():
    _test_eg_base()
    _test_eg_dump()
    _test_eg_query()
