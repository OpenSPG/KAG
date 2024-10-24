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
import os
from enum import Enum
from typing import Type, Dict, List

from knext.graph_algo.client import GraphAlgoClient
from kag.builder.model.sub_graph import SubGraph
from kag.interface.builder.writer_abc import SinkWriterABC
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


class AlterOperationEnum(str, Enum):
    Upsert = "UPSERT"
    Delete = "DELETE"


class KGWriter(SinkWriterABC):
    """
    A class that extends `SinkWriter` to handle writing data into a Neo4j knowledge graph.

    This class is responsible for configuring the graph store based on environment variables and
    an optional project ID, initializing the Neo4j client, and setting up the schema.
    It also manages semantic indexing and multi-threaded operations.
    """

    def __init__(self, project_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id or os.getenv("KAG_PROJECT_ID")
        self.client = GraphAlgoClient(project_id=project_id)

    @property
    def input_types(self) -> Type[Input]:
        return SubGraph

    @property
    def output_types(self) -> Type[Output]:
        return None

    def invoke(
        self, input: Input, alter_operation: str = AlterOperationEnum.Upsert, lead_to_builder: bool = False
    ) -> List[Output]:
        """
        Invokes the specified operation (upsert or delete) on the graph store.

        Args:
            input (Input): The input object representing the subgraph to operate on.
            alter_operation (str): The type of operation to perform (Upsert or Delete).
            lead_to_builder (str): enable lead to event infer builder

        Returns:
            List[Output]: A list of output objects (currently always [None]).
        """
        self.client.write_graph(sub_graph=input.to_dict(), operation=alter_operation, lead_to_builder=lead_to_builder)
        return [None]

    def _handle(self, input: Dict, alter_operation: str, **kwargs):
        """The calling interface provided for SPGServer."""
        _input = self.input_types.from_dict(input)
        _output = self.invoke(_input, alter_operation)
        return None
