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
import asyncio
from typing import Dict, Type, List

from kag.interface import LLMClient
from tenacity import stop_after_attempt, retry, wait_exponential

from kag.interface import ExtractorABC, PromptABC, ExternalGraphLoaderABC

from kag.common.utils import processing_phrases, to_camel_case
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.model.sub_graph import SubGraph
from kag.builder.prompt.utils import init_prompt_with_fallback
from knext.schema.client import OTHER_TYPE, CHUNK_TYPE, BASIC_TYPES
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient

logger = logging.getLogger(__name__)


@ExtractorABC.register("schema_free")
@ExtractorABC.register("schema_free_extractor")
class SchemaFreeExtractor(ExtractorABC):
    """
    A class for extracting knowledge graph subgraphs from text using a large language model (LLM).
    Inherits from the Extractor base class.

    Attributes:
        llm (LLMClient): The large language model client used for text processing.
        schema (SchemaClient): The schema client used to load the schema for the project.
        ner_prompt (PromptABC): The prompt used for named entity recognition.
        std_prompt (PromptABC): The prompt used for named entity standardization.
        triple_prompt (PromptABC): The prompt used for triple extraction.
        external_graph (ExternalGraphLoaderABC): The external graph loader used for additional NER.
    """

    def __init__(
        self,
        llm: LLMClient,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        triple_prompt: PromptABC = None,
        external_graph: ExternalGraphLoaderABC = None,
        **kwargs,
    ):
        """
        Initializes the KAGExtractor with the specified parameters.

        Args:
            llm (LLMClient): The large language model client.
            ner_prompt (PromptABC, optional): The prompt for named entity recognition. Defaults to None.
            std_prompt (PromptABC, optional): The prompt for named entity standardization. Defaults to None.
            triple_prompt (PromptABC, optional): The prompt for triple extraction. Defaults to None.
            external_graph (ExternalGraphLoaderABC, optional): The external graph loader. Defaults to None.
        """
        super().__init__(**kwargs)
        self.llm = llm
        self.schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
        self.ner_prompt = ner_prompt
        self.std_prompt = std_prompt
        self.triple_prompt = triple_prompt

        biz_scene = self.kag_project_config.biz_scene
        if self.ner_prompt is None:
            self.ner_prompt = init_prompt_with_fallback("ner", biz_scene)
        if self.std_prompt is None:
            self.std_prompt = init_prompt_with_fallback("std", biz_scene)
        if self.triple_prompt is None:
            self.triple_prompt = init_prompt_with_fallback("triple", biz_scene)

        self.external_graph = external_graph
        table_extractor_config = {
            "type": "table_extractor",
            "llm": self.llm.to_config(),
            "table_context_prompt": "table_context",
            "table_row_col_summary_prompt": "table_row_col_summary",
        }
        self.table_extractor = ExtractorABC.from_config(table_extractor_config)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @staticmethod
    def output_indices() -> List[str]:
        return ["spo_graph_index", "chunk_index"]

    def _named_entity_recognition_llm(self, passage: str):
        ner_result = self.llm.invoke(
            {"input": passage}, self.ner_prompt, with_except=False
        )
        return ner_result

    async def _anamed_entity_recognition_llm(self, passage: str):
        ner_result = await self.llm.ainvoke(
            {"input": passage}, self.ner_prompt, with_except=False
        )
        return ner_result

    def _named_entity_recognition_process(self, passage, ner_result):
        if self.external_graph:
            extra_ner_result = self.external_graph.ner(passage)
        else:
            extra_ner_result = []
        output = []
        dedup = set()
        for item in extra_ner_result:
            name = item.name
            label = item.label
            spg_type = self.schema.get(label)
            if spg_type is None:
                label = "Others"
                item.label = label
            description = item.properties.get("desc", "")
            semantic_type = item.properties.get("semanticType", label)
            if name not in dedup:
                dedup.add(name)
                output.append(
                    {
                        "name": name,
                        "type": semantic_type,
                        "category": label,
                        "description": description,
                    }
                )
        for item in ner_result:
            name = item.get("name", None)
            if name and name not in dedup:
                dedup.add(name)
                output.append(item)
        return output

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def named_entity_recognition(self, passage: str):
        """
        Performs named entity recognition on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the named entity recognition operation.
        """
        ner_result = self._named_entity_recognition_llm(passage)
        return self._named_entity_recognition_process(passage, ner_result)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def anamed_entity_recognition(self, passage: str):
        """
        Performs named entity recognition on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the named entity recognition operation.
        """
        ner_result = await self._anamed_entity_recognition_llm(passage)
        return self._named_entity_recognition_process(passage, ner_result)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
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
            {"input": passage, "named_entities": entities},
            self.std_prompt,
            with_except=False,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def anamed_entity_standardization(self, passage: str, entities: List[Dict]):
        """
        Standardizes named entities.

        Args:
            passage (str): The input text passage.
            entities (List[Dict]): A list of recognized named entities.

        Returns:
            Standardized entity information.
        """
        return await self.llm.ainvoke(
            {"input": passage, "named_entities": entities},
            self.std_prompt,
            with_except=False,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
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
            {"input": passage, "entity_list": entities},
            self.triple_prompt,
            with_except=False,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def atriples_extraction(self, passage: str, entities: List[Dict]):
        """
        Extracts triples (subject-predicate-object structures) from a given text passage based on identified entities.
        Args:
            passage (str): The text to extract triples from.
            entities (List[Dict]): A list of entities identified in the text.
        Returns:
            The result of the triples extraction operation.
        """

        return await self.llm.ainvoke(
            {"input": passage, "entity_list": entities},
            self.triple_prompt,
            with_except=False,
        )

    def assemble_sub_graph_with_spg_records(self, entities: List[Dict]):
        """
        Assembles a subgraph using SPG records.

        Args:
            entities (List[Dict]): A list of entities to be used for subgraph assembly.

        Returns:
            The assembled subgraph and the updated list of entities.
        """
        sub_graph = SubGraph([], [])
        for record in entities:
            s_name = record.get("name", "")
            s_label = record.get("category", "")
            properties = record.get("properties", {})
            tmp_properties = copy.deepcopy(properties)
            spg_type = self.schema.get(s_label)
            if spg_type is None:
                s_label = "Others"
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
        Returns:
            The constructed subgraph.

        """

        def get_category_and_name(entities_data, entity_name):
            for entity in entities_data:
                if processing_phrases(entity["name"]) == processing_phrases(
                    entity_name
                ):
                    return entity["category"], entity["name"]
            return None, None

        for tri in triples:
            if tri is None or len(tri) != 3:
                continue
            s_category, s_name = get_category_and_name(entities, tri[0])
            tri[0] = processing_phrases(tri[0])
            if tri[0] == "":
                continue
            if s_category is None:
                s_category = OTHER_TYPE
                s_name = tri[0]
                sub_graph.add_node(s_name, s_name, s_category)
            o_category, o_name = get_category_and_name(entities, tri[2])
            if o_name == "":
                continue
            if o_category is None:
                o_name = processing_phrases(tri[2])
                o_category = OTHER_TYPE
                sub_graph.add_node(o_name, o_name, o_category)
            edge_type = to_camel_case(tri[1])
            if edge_type:
                sub_graph.add_edge(s_name, s_category, edge_type, o_name, o_category)

        return sub_graph

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
            The constructed subgraph.
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
            name = processing_phrases(ent["name"])
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
        try:
            tmp_dict = {}
            for tmp_entity in entities_with_official_name:
                if "name" in tmp_entity:
                    name = tmp_entity["name"]
                elif "entity" in tmp_entity:
                    name = tmp_entity["entity"]
                else:
                    continue
                category = tmp_entity["category"]
                if self.schema.get(category, None) is None:
                    category = "Others"
                official_name = tmp_entity["official_name"]
                key = f"{category}{name}"
                tmp_dict[key] = official_name

            for tmp_entity in source_entities:
                name = tmp_entity["name"]
                category = tmp_entity["category"]
                key = f"{category}{name}"
                if key in tmp_dict:
                    official_name = tmp_dict[key]
                    tmp_entity["official_name"] = official_name
        except Exception as e:
            logger.warn(f"failed to process official name, info: {e}")

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        print("Enter schema free extractor======================")
        logger.info("Enter schema free extractor======================")
        title = input.name
        passage = title + "\n" + input.content
        out = []
        entities = self.named_entity_recognition(passage)
        sub_graph, entities = self.assemble_sub_graph_with_spg_records(entities)
        filtered_entities = [
            {k: v for k, v in ent.items() if k in ["name", "category"]}
            for ent in entities
        ]
        triples = (self.triples_extraction(passage, filtered_entities),)
        std_entities = self.named_entity_standardization(passage, filtered_entities)
        self.append_official_name(entities, std_entities)
        self.assemble_sub_graph(sub_graph, input, entities, triples)
        out.append(sub_graph)
        print("Exit schema free extractor=================")
        logger.info("Exit schema free extractor=================")
        return out

    async def _ainvoke(self, input: Input, **kwargs) -> List[Output]:
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

        title = input.name
        passage = title + "\n" + input.content
        out = []
        entities = await self.anamed_entity_recognition(passage)
        sub_graph, entities = self.assemble_sub_graph_with_spg_records(entities)
        filtered_entities = [
            {k: v for k, v in ent.items() if k in ["name", "category"]}
            for ent in entities
        ]
        triples, std_entities = await asyncio.gather(
            self.atriples_extraction(passage, filtered_entities),
            self.anamed_entity_standardization(passage, filtered_entities),
        )

        self.append_official_name(entities, std_entities)
        self.assemble_sub_graph(sub_graph, input, entities, triples)
        out.append(sub_graph)
        return out
