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
import os
from typing import Dict, Type, List

from tenacity import stop_after_attempt, retry

from kag.builder.prompt.spg_prompt import SPG_KGPrompt
from kag.interface.builder import ExtractorABC
from kag.common.base.prompt_op import PromptOp
from knext.schema.client import OTHER_TYPE, CHUNK_TYPE, BASIC_TYPES
from kag.common.utils import processing_phrases, to_camel_case
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from knext.schema.model.base import SpgTypeEnum

logger = logging.getLogger(__name__)


class KAGExtractor(ExtractorABC):
    """
    A class for extracting knowledge graph subgraphs from text using a large language model (LLM).
    Inherits from the Extractor base class.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        self.prompt_config = self.config.get("prompt", {})
        self.biz_scene = self.prompt_config.get("biz_scene") or os.getenv(
            "KAG_PROMPT_BIZ_SCENE", "default"
        )
        self.language = self.prompt_config.get("language") or os.getenv(
            "KAG_PROMPT_LANGUAGE", "en"
        )
        self.schema = SchemaClient(project_id=self.project_id).load()
        self.ner_prompt = PromptOp.load(self.biz_scene, "ner")(
            language=self.language, project_id=self.project_id
        )
        self.std_prompt = PromptOp.load(self.biz_scene, "std")(language=self.language)
        self.triple_prompt = PromptOp.load(self.biz_scene, "triple")(
            language=self.language
        )
        self.kg_types = []
        for type_name, spg_type in self.schema.items():
            if type_name in SPG_KGPrompt.ignored_types:
                continue
            if spg_type.spg_type_enum == SpgTypeEnum.Concept:
                continue
            properties = list(spg_type.properties.keys())
            for p in properties:
                if p not in SPG_KGPrompt.ignored_properties:
                    self.kg_types.append(type_name)
                    break
        if self.kg_types:
            self.kg_prompt = SPG_KGPrompt(
                self.kg_types, language=self.language, project_id=self.project_id
            )

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
        if self.kg_types:
            kg_result = self.llm.invoke({"input": passage}, self.kg_prompt)
        else:
            kg_result = []
        ner_result = self.llm.invoke({"input": passage}, self.ner_prompt)
        return kg_result + ner_result

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
        return self.llm.invoke(
            {"input": passage, "named_entities": entities}, self.std_prompt
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
        return self.llm.invoke(
            {"input": passage, "entity_list": entities}, self.triple_prompt
        )

    def assemble_sub_graph_with_spg_records(self, entities: List[Dict]):
        sub_graph = SubGraph([], [])
        for record in entities:
            s_name = record.get("entity", "")
            s_label = record.get("category", "")
            properties = record.get("properties", {})
            tmp_properties = copy.deepcopy(properties)
            spg_type = self.schema.get(s_label)
            for prop_name, prop_value in properties.items():
                if prop_value == "NAN":
                    tmp_properties.pop(prop_name)
                    continue
                if prop_name in spg_type.properties:
                    from knext.schema.model.property import Property

                    prop: Property = spg_type.properties.get(prop_name)
                    o_label = prop.object_type_name_en
                    if o_label not in BASIC_TYPES:
                        if isinstance(prop_value, str):
                            prop_value = [prop_value]
                        for o_name in prop_value:
                            sub_graph.add_node(id=o_name, name=o_name, label=o_label)
                            sub_graph.add_edge(
                                s_id=s_name,
                                s_label=s_label,
                                p=prop_name,
                                o_id=o_name,
                                o_label=o_label,
                            )
                        tmp_properties.pop(prop_name)
            record["properties"] = tmp_properties
            sub_graph.add_node(
                id=s_name, name=s_name, label=s_label, properties=properties
            )
        return sub_graph, entities

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

            edge_type = to_camel_case(tri[1])
            if edge_type:
                sub_graph.add_edge(tri[0], s_category, edge_type, tri[2], o_category)

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
                **chunk.kwargs,
            },
        )
        sub_graph.id = chunk.id
        return sub_graph

    def assemble_sub_graph(
        self,
        sub_graph: SubGraph,
        chunk: Chunk,
        entities: List[Dict],
        triples: List[list],
    ):
        """
        Integrates entity and triple information into a subgraph, and associates it with a chunk of text.
        Args:
            sub_graph (SubGraph): The subgraph to be assembled.
            chunk (Chunk): The chunk of text the subgraph is about.
            entities (List[Dict]): A list of entities identified in the chunk.
            triples (List[list]): A list of triples representing relationships between entities.
        Returns:
            SubGraph: The constructed subgraph.
        """
        self.assemble_sub_graph_with_entities(sub_graph, entities)
        self.assemble_sub_graph_with_triples(sub_graph, entities, triples)
        self.assemble_sub_graph_with_chunk(sub_graph, chunk)
        return sub_graph

    def assemble_sub_graph_with_entities(
        self, sub_graph: SubGraph, entities: List[Dict]
    ):
        """
        Assembles a subgraph using named entities.

        Args:
            sub_graph (SubGraph): The subgraph object to be assembled.
            entities (List[Dict]): A list containing entity information.
        """

        for ent in entities:
            name = processing_phrases(ent["entity"])
            sub_graph.add_node(
                name,
                name,
                ent["category"],
                {
                    "desc": ent.get("description", ""),
                    "semanticType": ent.get("type", ""),
                    **ent.get("properties", {}),
                },
            )

            if "official_name" in ent:
                official_name = processing_phrases(ent["official_name"])
                if official_name != name:
                    sub_graph.add_node(
                        official_name,
                        official_name,
                        ent["category"],
                        {
                            "desc": ent.get("description", ""),
                            "semanticType": ent.get("type", ""),
                            **ent.get("properties", {}),
                        },
                    )
                    sub_graph.add_edge(
                        name,
                        ent["category"],
                        "OfficialName",
                        official_name,
                        ent["category"],
                    )

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
            name = tmp_entity["entity"]
            category = tmp_entity["category"]
            official_name = tmp_entity["official_name"]
            key = f"{category}{name}"
            tmp_dict[key] = official_name

        for tmp_entity in source_entities:
            name = tmp_entity["entity"]
            category = tmp_entity["category"]
            key = f"{category}{name}"
            if key in tmp_dict:
                official_name = tmp_dict[key]
                tmp_entity["official_name"] = official_name

    def quoteStr(self, input: str) -> str:
        return f"""{input}"""

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        title = input.name
        passage = self.quoteStr(title + "\n" + input.content)

        try:
            entities = self.named_entity_recognition(passage)
            sub_graph, entities = self.assemble_sub_graph_with_spg_records(entities)
            filtered_entities = [
                {k: v for k, v in ent.items() if k in ["entity", "category"]}
                for ent in entities
            ]
            triples = self.triples_extraction(passage, filtered_entities)
            std_entities = self.named_entity_standardization(passage, filtered_entities)
            self.append_official_name(entities, std_entities)
            self.assemble_sub_graph(sub_graph, input, entities, triples)
            return [sub_graph]
        except Exception as e:
            import traceback

            traceback.print_exc()
            logger.info(e)
        return []
