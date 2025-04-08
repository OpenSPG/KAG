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
import copy
import logging
from typing import Dict, Type, List

from kag.interface import LLMClient
from tenacity import stop_after_attempt, retry

from kag.interface import DecomposerABC, PromptABC, ExternalGraphLoaderABC
from kag.common.utils import generate_hash_id
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.utils import processing_phrases, to_camel_case
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from kag.builder.prompt.utils import init_prompt_with_fallback
from knext.schema.client import OTHER_TYPE, CHUNK_TYPE, BASIC_TYPES
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient

logger = logging.getLogger(__name__)


@DecomposerABC.register("atomic_question_chunk")
@DecomposerABC.register("atomic_question_chunk_decomposer")
class AtomicQuestionChunkDecomposer(DecomposerABC):
    """
    A class for extracting knowledge graph subgraphs from text using a large language model (LLM).
    Inherits from the Extractor base class.

    Attributes:
        llm (LLMClient): The large language model client used for text processing.
        schema (SchemaClient): The schema client used to load the schema for the project.
        decomposition_prompt (PromptABC): Atomic question demoposition prompt.
    """

    def __init__(
        self,
        llm: LLMClient,
        decomposition_prompt: PromptABC = None
    ):
        """
        Initializes the Decomposer with the specified parameters.

        Args:
            llm (LLMClient): The large language model client.
            decomposition_prompt (PromptABC): Atomic question demoposition prompt.
        """
        super().__init__()
        self.llm = llm
        self.schema = SchemaClient(project_id=KAG_PROJECT_CONF.project_id).load()
        self.decomposition_prompt = decomposition_prompt

        biz_scene = KAG_PROJECT_CONF.biz_scene
        if self.decomposition_prompt is None:
            self.decomposition_prompt = init_prompt_with_fallback("decomposition", biz_scene)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @retry(stop=stop_after_attempt(3))
    def atomic_question_chunk_decomposition(self, passage: str):
        """
        Performs atomic questions on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the Q&As.
        """
        decomposition_result = self.llm.invoke(
            {"input": passage}, self.decomposition_prompt, with_except=False
        )

        return decomposition_result

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

    def assemble_sub_graph_with_atomic_questions(
        self, sub_graph: SubGraph, atomic_question: List[Dict]
    ):
        """
        Assembles a subgraph using atomic_questions.

        Args:
            sub_graph (SubGraph): The subgraph object to be assembled.
            atomic_question (List[Dict]): A list containing entity information.
        """

        for qa in atomic_question:
            question = qa
            sub_graph.add_node(
                generate_hash_id(question),
                question,
                "AtomicQuestion",
                {
                    "id": question,
                    "name": question,
                    "content": f"{question}",
                },
            )

    def assemble_sub_graph(
            self,
            chunk: Chunk,
            atomic_questions: List[Dict],
    ):
        """
        Integrates entity and triple information into a subgraph, and associates it with a chunk of text.
        Args:
            chunk (Chunk): The chunk of text the subgraph is about.
            atomic_questions (List[Dict]): A list of entities identified in the chunk.
        Returns:
            The constructed subgraph.
        """
        sub_graph = SubGraph([],[])
        self.assemble_sub_graph_with_atomic_questions(sub_graph, atomic_questions)
        self.assemble_sub_graph_with_chunk(sub_graph, chunk)
        return sub_graph

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic decomposer to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """

        title = input.name
        passage = title + "\n" + input.content
        out = []
        atomic_questions = self.atomic_question_chunk_decomposition(passage)
        sub_graph = self.assemble_sub_graph(input, atomic_questions)
        out.append(sub_graph)
        return out
