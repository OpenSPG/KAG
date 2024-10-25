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

from typing import List, Sequence, Dict, Type

from kag.builder.model.sub_graph import SubGraph
from kag.interface.builder import AlignerABC
from knext.common.base.runnable import Input, Output


class KAGPostProcessorAligner(AlignerABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def invoke(self, input: List[SubGraph], **kwargs) -> SubGraph:
        merged_sub_graph = SubGraph(nodes=[], edges=[])
        for sub_graph in input:
            for node in sub_graph.nodes:
                if node not in merged_sub_graph.nodes:
                    merged_sub_graph.nodes.append(node)
            for edge in sub_graph.edges:
                if edge not in merged_sub_graph.edges:
                    merged_sub_graph.edges.append(edge)
        return merged_sub_graph

    def _handle(self, input: Sequence[Dict]) -> Dict:
        _input = [self.input_types.from_dict(i) for i in input]
        _output = self.invoke(_input)
        return _output.to_dict()

    def batch(self, inputs: List[Input], **kwargs) -> List[Output]:
        pass
