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

from typing import List, Type

from kag.interface.builder import AlignerABC
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output

from kag.common.semantic_infer import SemanticEnhance


class SemanticAligner(AlignerABC, SemanticEnhance):
    """
    A class for semantic alignment and enhancement, inheriting from Aligner and SemanticEnhance.
    """

    def __init__(self, **kwargs):
        AlignerABC.__init__(self, **kwargs)
        SemanticEnhance.__init__(self, **kwargs)

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def invoke(self, input: SubGraph, **kwargs) -> List[SubGraph]:
        """
        Generates and adds concept nodes based on extracted entities and their context.

        Args:
            input (SubGraph): The input subgraph.
            **kwargs: Additional keyword arguments.

        Returns:
            List[SubGraph]: A list containing the updated subgraph.
        """
        expanded_concept_nodes = []
        expanded_concept_edges = []

        context = [
            node.properties.get("content")
            for node in input.nodes if node.label == 'Chunk'
        ]
        context = context[0] if context else None
        _dedup_keys = set()
        for node in input.nodes:
            if node.id == "" or node.name == "" or node.label == 'Chunk':
                continue
            if node.name in _dedup_keys:
                continue
            _dedup_keys.add(node.name)
            expand_dict = self.expand_semantic_concept(node.name, context=context, target=None)
            expand_nodes = [
                {
                    "id": info["name"], "name": info["name"],
                    "label": self.concept_label,
                    "properties": {"desc": info["desc"]}
                }
                for info in expand_dict
            ]
            expanded_concept_nodes.extend(expand_nodes)
            path_nodes = [node.to_dict()] + expand_nodes
            # entity -> concept, concept -> concept
            for ix, concept in enumerate(path_nodes):
                if ix == 0:
                    continue
                expanded_concept_edges.append({
                    "s_id": path_nodes[ix-1]["id"],
                    "s_label": path_nodes[ix-1]["label"],
                    "p": self.hyper_edge,
                    "o_id": path_nodes[ix]["id"],
                    "o_label": path_nodes[ix]["label"]
                })
        [input.add_node(**n) for n in expanded_concept_nodes]
        [input.add_edge(**e) for e in expanded_concept_edges]

        return [input]
