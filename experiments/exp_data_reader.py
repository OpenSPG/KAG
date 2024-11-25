# -*- coding: utf-8 -*-
# 直接从文件中读取抽取结果，用于实验。

import json
from typing import List, Type, Dict

from kag.builder.component.base import SourceReader
from kag.builder.model.sub_graph import SubGraph
from kag.common.base.runnable import Input, Output


class PreExtractedSubGraph(SourceReader):

    def __init__(self, with_sim_edge=True, with_entity_norm=True, with_hyper_expand=True):
        super(PreExtractedSubGraph, self).__init__()
        self.with_sim_edge = bool(with_sim_edge)
        self.with_entity_norm = bool(with_entity_norm)
        self.with_hyper_expand = bool(with_hyper_expand)

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return SubGraph

    @staticmethod
    def _filter_official_nodes_edges(subgraph: Dict):
        official_names = {
            edge["to"] for edge in subgraph['resultEdges'] 
            if edge.get('label') == 'OfficialName'
        }

        _nodes = [
            node for node in subgraph['resultNodes']
            if node["name"] not in official_names
        ]
        _edges = [
            edge for edge in subgraph['resultEdges']
            if edge.get('label') != 'OfficialName'
        ]
        return {"resultNodes": _nodes, "resultEdges": _edges}

    @staticmethod
    def _filter_similarity_edges(subgraph: Dict):
        _edges = [
            edge for edge in subgraph['resultEdges']
            if edge.get('label') != 'similarity'
        ]
        return {"resultNodes": subgraph["resultNodes"], "resultEdges": _edges}

    @staticmethod
    def _filter_semantic_nodes_edges(subgraph: Dict):
        _nodes = [
            node for node in subgraph['resultNodes']
            if node["label"] != 'SemanticConcept'
        ]
        _edges = [
            edge for edge in subgraph['resultEdges']
            if edge.get('label') != 'SemanticIsA'
        ]
        return {"resultNodes": _nodes, "resultEdges": _edges}

    def invoke(self, input: str, **kwargs) -> List[Output]:
        subgraph_list = []
        for line in open(input, 'r').readlines():
            data = json.loads(line.strip())
            if not self.with_entity_norm:
                data = self._filter_official_nodes_edges(data)
            if not self.with_hyper_expand:
                data = self._filter_semantic_nodes_edges(data)
            if not self.with_sim_edge:
                data = self._filter_similarity_edges(data)
            subgraph_list.append(SubGraph.from_dict(data))
        return subgraph_list
