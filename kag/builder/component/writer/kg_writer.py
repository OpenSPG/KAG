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
from enum import Enum
from typing import Type, Dict, List

from knext.graph.client import GraphClient
from kag.builder.model.sub_graph import SubGraph
from kag.interface import SinkWriterABC
from kag.common.conf import KAG_PROJECT_CONF
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


class AlterOperationEnum(str, Enum):
    Upsert = "UPSERT"
    Delete = "DELETE"


@SinkWriterABC.register("kg", as_default=True)
@SinkWriterABC.register("kg_writer", as_default=True)
class KGWriter(SinkWriterABC):
    """
    A class for writing SubGraphs to a Knowledge Graph (KG) storage.

    This class inherits from SinkWriterABC and provides the functionality to write SubGraphs
    to a Knowledge Graph storage system. It supports operations like upsert and delete.
    """

    def __init__(self, project_id: int = None, **kwargs):
        """
        Initializes the KGWriter with the specified project ID.

        Args:
            project_id (int): The ID of the project associated with the KG. Defaults to None.
            **kwargs: Additional keyword arguments passed to the superclass.
        """
        super().__init__(**kwargs)
        if project_id is None:
            self.project_id = KAG_PROJECT_CONF.project_id
        else:
            self.project_id = project_id
        self.client = GraphClient(project_id=project_id)

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
        namespace = KAG_PROJECT_CONF.namespace
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

    def invoke(
        self,
        input: Input,
        alter_operation: str = AlterOperationEnum.Upsert,
        lead_to_builder: bool = False,
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
        logger.debug(f"final graph to write: {input}")
        self.client.write_graph(
            sub_graph=input.to_dict(),
            operation=alter_operation,
            lead_to_builder=lead_to_builder,
        )
        return [input]

    def _handle(self, input: Dict, alter_operation: str, **kwargs):
        """
        The calling interface provided for SPGServer.

        Args:
            input (Dict): The input dictionary representing the subgraph to operate on.
            alter_operation (str): The type of operation to perform (Upsert or Delete).
            **kwargs: Additional keyword arguments.

        Returns:
            None: This method currently returns None.
        """
        _input = self.input_types.from_dict(input)
        _output = self.invoke(_input, alter_operation)  # noqa

        return None
