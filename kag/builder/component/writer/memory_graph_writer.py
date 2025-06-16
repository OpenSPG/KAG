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
from typing import Type, List

from kag.builder.model.sub_graph import SubGraph
from kag.interface import SinkWriterABC
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


@SinkWriterABC.register("memory_graph")
@SinkWriterABC.register("memory_graph_writer")
class MemoryGraphWriter(SinkWriterABC):
    """
    A class for writing SubGraphs to a Memory based graph storage.

    This class inherits from SinkWriterABC and provides the functionality to write SubGraphs
    to a Knowledge Graph storage system. It supports operations like upsert and delete.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return None

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

    def standarlize_graph(self, graph):
        for node in graph.nodes:
            node.label = self.format_label(node.label)
        for edge in graph.edges:
            edge.from_type = self.format_label(edge.from_type)
            edge.to_type = self.format_label(edge.to_type)

        for node in graph.nodes:
            for k, v in node.properties.items():
                if k.startswith("_"):
                    continue
                if not isinstance(v, str):
                    node.properties[k] = json.dumps(v, ensure_ascii=False)
        for edge in graph.edges:
            for k, v in edge.properties.items():
                if k.startswith("_"):
                    continue
                if not isinstance(v, str):
                    edge.properties[k] = json.dumps(v, ensure_ascii=False)

        return graph

    def _invoke(
        self,
        input: Input,
        **kwargs,
    ) -> List[Output]:
        """
        Invokes the specified operation (upsert or delete) on the graph store.

        Args:
            input (Input): The input object representing the subgraph to operate on.
            alter_operation (str): The type of operation to perform (Upsert or Delete). Defaults to Upsert.
            lead_to_builder (bool): Enable lead to event infer builder. Defaults to False.

        Returns:
            List[Output]: A list of output objects (currently always [None]).
        """
        input = self.standarlize_graph(input)
        return [input]
