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
from typing import Type, List


from kag.interface import ExtractorABC, ExternalGraphLoaderABC

from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.model.sub_graph import SubGraph
from knext.schema.client import CHUNK_TYPE
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


@ExtractorABC.register("naive_rag_extractor")
class NaiveRagExtractor(ExtractorABC):
    """
    A class for extracting knowledge graph subgraphs from text using a large language model (LLM).
    Inherits from the Extractor base class.

    Attributes:
        external_graph (ExternalGraphLoaderABC): The external graph loader used for additional named entity recognition.
        table_extractor (ExtractorABC): The extractor used for processing table data.
    """

    def __init__(
        self,
        external_graph: ExternalGraphLoaderABC = None,
        table_extractor: ExtractorABC = None,
    ):
        """
        Initializes the NaiveRagExtractor with the specified parameters.

        Args:
            external_graph (ExternalGraphLoaderABC, optional): The external graph loader for additional named entity recognition. Defaults to None.
            table_extractor (ExtractorABC, optional): The extractor for processing table data. Defaults to None.
        """
        super().__init__()
        self.external_graph = external_graph
        self.table_extractor = table_extractor

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @staticmethod
    def output_indices() -> List[str]:
        return ["chunk_index"]

    @staticmethod
    def assemble_sub_graph_with_chunk(sub_graph: SubGraph, chunk: Chunk):
        """
        Associates a Chunk object with the subgraph, adding it as a node and connecting it with existing nodes.
        Args:
            sub_graph (SubGraph): The subgraph to add the chunk information to.
            chunk (Chunk): The chunk object containing the text and metadata.
        Returns:
            The constructed subgraph.
        """
        for node in sub_graph.nodes:
            sub_graph.add_edge(node.id, node.label, "source", chunk.id, CHUNK_TYPE)
        sub_graph.add_node(
            chunk.id,
            chunk.name,
            CHUNK_TYPE,
            {
                "id": chunk.id,
                "name": chunk.name,
                "content": f"{chunk.name}\n{chunk.content}",
                **chunk.kwargs,
            },
        )
        sub_graph.id = chunk.id
        return sub_graph

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """

        if self.table_extractor is not None and input.type == ChunkTypeEnum.Table:
            return self.table_extractor._invoke(input)

        out = []
        sub_graph = SubGraph([], [])
        sub_graph = self.assemble_sub_graph_with_chunk(sub_graph, input)

        out.append(sub_graph)
        return out
