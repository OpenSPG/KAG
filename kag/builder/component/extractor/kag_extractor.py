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
from typing import Dict, Type, List

from tenacity import stop_after_attempt, retry

from kag.builder.component.base import Extractor
from kag.common.base.prompt_op import PromptOp
from kag.schema.client import OTHER_TYPE, CHUNK_TYPE
from kag.common.utils import processing_phrases, to_camel_case
from kag.common.llm.client.llm_client import LLMClient
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from kag.common.base.runnable import Input, Output
from kag.schema.client import SchemaClient

logger = logging.getLogger(__name__)


class KAGExtractor(Extractor):
    """
    A class for extracting knowledge graph sub-graphs from text using a large language model (LLM).
    Inherits from the Extractor base class.
    """

    def __init__(self):
        super().__init__()
        self.biz_scene = os.getenv("KAG_PROMPT_BIZ_SCENE", "default")
        self.language = os.getenv("KAG_PROMPT_LANGUAGE", "en")
        self.schema = SchemaClient().load()
        self.llm_config = eval(os.getenv("KAG_LLM", "{}"))
        self.client = LLMClient.from_config(self.llm_config)
        self.triple_prompt = PromptOp.load(self.biz_scene, "triple")(language=self.language)
        self.with_onto_label = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_FIX_ONTO", "True"))
        self.ner_prompt = PromptOp.load(self.biz_scene, "ner")(language=self.language)
        self.with_entity_norm = eval(os.getenv("KAG_INDEXER_WITH_SEMANTIC_ENTITY_NORM", "True"))
        if self.with_entity_norm:
            self.std_prompt = PromptOp.load(self.biz_scene, "std")(language=self.language)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @retry(stop=stop_after_attempt(3))
    def named_entity_recognition(self, passage: str):
        """
        Performs named entity recognition on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the named entity recognition operation.
        """
        return self.client.invoke({"input": passage}, self.ner_prompt)

    @retry(stop=stop_after_attempt(3))
    def named_entity_standardization(self, passage: str, entities: List[Dict]):
        """
        Standardizes named entities.

        Args:
            passage (str): The input text passage.
            entities (List[Dict]): A list of recognized named entities.

        Returns:
            Standardized entity information.
        """
        tmp = []
        for ent in entities:
            if "entity" in ent and "category" in ent:
                tmp.append({"entity": ent["entity"], "category": ent["category"]})
        return self.client.invoke(
            {"input": passage, "named_entities": tmp}, self.std_prompt
        )

    @retry(stop=stop_after_attempt(3))
    def triples_extraction(self, passage: str, entities: List[Dict]):
        """
        Extracts triples (subject-predicate-object structures) from a given text passage based on identified entities.
        Args:
            passage (str): The text to extract triples from.
            entities (List[Dict]): A list of entities identified in the text.
        Returns:
            The result of the triples extraction operation.
        """
        return self.client.invoke(
            {"input": passage, "entity_list": entities}, self.triple_prompt
        )

    @staticmethod
    def assemble_sub_graph_with_entities(sub_graph: SubGraph, entities: List[Dict]):
        """
        Assembles nodes in the subgraph based on a list of entities.
        Args:
            sub_graph (SubGraph): The subgraph to add nodes to.
            entities (List[Dict]): A list of entities, each with entity name, category, and type information.
        """
        for ent in entities:
            name = processing_phrases(ent["entity"])
            desc = ent.get("description")
            desc = f"{name}:{desc}" if desc else name
            sub_graph.add_node(
                name,
                name,
                ent["category"],
                {
                    "desc": desc,
                    "semanticType": ent.get("type", ""),
                },
            )

            official_name = processing_phrases(ent["official_name"]) if "official_name" in ent else None
            if official_name and official_name != name:
                sub_graph.add_node(
                    official_name,
                    official_name,
                    ent["category"],
                    {
                        "desc": ent.get("description", ""),
                        "semanticType": ent.get("type", ""),
                    },
                )
                sub_graph.add_edge(
                    name,
                    ent["category"],
                    "OfficialName",
                    official_name,
                    ent["category"],
                )

    @staticmethod
    def assemble_sub_graph_with_triples(
        sub_graph: SubGraph, entities: List[Dict], triples: List[list]
    ):
        """
        Assembles edges in the subgraph based on a list of triples and entities.
        Args:
            sub_graph (SubGraph): The subgraph to add edges to.
            entities (List[Dict]): A list of entities, for looking up category information.
            triples (List[list]): A list of triples, each representing a relationship to be added to the subgraph.
        """

        def get_category(entities_data, entity_name):
            for entity in entities_data:
                if entity["entity"] == entity_name:
                    return entity["category"]
            return None

        for tri in triples:
            if len(tri) != 3:
                continue
            s_category = get_category(entities, tri[0])
            tri[0] = processing_phrases(tri[0])
            if s_category is None:
                s_category = OTHER_TYPE
                sub_graph.add_node(tri[0], tri[0], s_category)
            o_category = get_category(entities, tri[2])
            tri[2] = processing_phrases(tri[2])
            if o_category is None:
                o_category = OTHER_TYPE
                sub_graph.add_node(tri[2], tri[2], o_category)

            sub_graph.add_edge(
                tri[0], s_category, to_camel_case(tri[1]), tri[2], o_category
            )

        return sub_graph

    @staticmethod
    def assemble_sub_graph_with_chunk(sub_graph: SubGraph, chunk: Chunk):
        """
        Associates a Chunk object with the subgraph, adding it as a node and connecting it with existing nodes.
        Args:
            sub_graph (SubGraph): The subgraph to add the chunk information to.
            chunk (Chunk): The chunk object containing the text and metadata.
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
                **chunk.kwargs
            },
        )
        sub_graph.id = chunk.id
        return sub_graph

    def assemble_sub_graph(
        self, chunk: Chunk, entities: List[Dict], triples: List[list]
    ):
        """
        Integrates entity and triple information into a subgraph, and associates it with a chunk of text.
        Args:
            chunk (Chunk): The chunk of text the subgraph is about.
            entities (List[Dict]): A list of entities identified in the chunk.
            triples (List[list]): A list of triples representing relationships between entities.
        Returns:
            SubGraph: The constructed subgraph.
        """
        sub_graph = SubGraph(nodes=[], edges=[])
        self.assemble_sub_graph_with_entities(sub_graph, entities)
        self.assemble_sub_graph_with_triples(sub_graph, entities, triples)
        self.assemble_sub_graph_with_chunk(sub_graph, chunk)
        return sub_graph

    def append_official_name(
        self, source_entities: List[Dict], entities_with_official_name: List[Dict]
    ):
        """
        Appends official names to entities.

        Args:
            source_entities (List[Dict]): A list of source entities.
            entities_with_official_name (List[Dict]): A list of entities with official names.
        """
        tmp_dict = {}
        for tmp_entity in entities_with_official_name:
            name = tmp_entity.get("entity", None)
            category = tmp_entity.get("category", None)
            official_name = tmp_entity.get("official_name", name)
            if name and category:
                key = f"{category}{name}"
                tmp_dict[key] = official_name

        for tmp_entity in source_entities:
            name = tmp_entity["entity"]
            category = tmp_entity["category"]
            key = f"{category}{name}"
            if key in tmp_dict:
                official_name = tmp_dict[key]
                tmp_entity["official_name"] = official_name
            else:
                tmp_entity["official_name"] = name

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes an input chunk to extract and assemble a subgraph, then returns the result.
        Args:
            input (Input): The input chunk of text.
            **kwargs: Additional keyword arguments.
        Returns:
            List[Output]: A list containing the extracted subgraph.
        """
        title = input.name
        passage = title + "\n" + input.content

        try:
            entities = self.named_entity_recognition(passage)
            triples = self.triples_extraction(passage, entities)
            if self.with_entity_norm:
                std_entities = self.named_entity_standardization(passage, entities)
                self.append_official_name(entities, std_entities)
            sub_graph = self.assemble_sub_graph(input, entities, triples)
            return [sub_graph]
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.info(e)
        return []
