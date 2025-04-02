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

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.utils import processing_phrases, to_camel_case
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from kag.builder.prompt.utils import init_prompt_with_fallback
from knext.schema.client import OTHER_TYPE, CHUNK_TYPE, BASIC_TYPES
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC,generate_gql_id_params
from kag.solver.tools.graph_api.model.table_model import TableData

logger = logging.getLogger(__name__)


@DecomposerABC.register("atomic_question_kb")
@DecomposerABC.register("atomic_question_kb_decomposer")
class AtomicQuestionKBDecomposer(DecomposerABC):
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
        decomposition_prompt: PromptABC = None,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        triple_prompt: PromptABC = None,
        graph_api: GraphApiABC = None,
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
        self.schema_utils: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.decomposition_prompt = decomposition_prompt
        self.ner_prompt = ner_prompt
        self.std_prompt = std_prompt
        self.triple_prompt = triple_prompt
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        biz_scene = KAG_PROJECT_CONF.biz_scene
        if self.decomposition_prompt is None:
            self.decomposition_prompt = init_prompt_with_fallback("decomposition", biz_scene)
        if self.ner_prompt is None:
            self.ner_prompt = init_prompt_with_fallback("ner", biz_scene)
        if self.std_prompt is None:
            self.std_prompt = init_prompt_with_fallback("std", biz_scene)
        if self.triple_prompt is None:
            self.triple_prompt = init_prompt_with_fallback("triple", biz_scene)

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    @retry(stop=stop_after_attempt(3))
    def get_atomic_questions(self, passage: str):
        """
        Performs atomic questions on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the Q&As.
        """
        matched_atomic_quesrions = []
        atomic_question_label = self.schema_utils.get_label_within_prefix('AtomicQuestion')
        chunk_label = self.schema_utils.get_label_within_prefix(CHUNK_TYPE)
        s_id_param = generate_gql_id_params([passage])
        dsl_query = f"""
                    MATCH (s:`{chunk_label}`)-[p:rdf_expand()]-(o:`{atomic_question_label}`)
                    WHERE s.id in $sid
                    )
                    RETURN s,p,o,s.id,o.id
                    """
        table: TableData = self.graph_api.execute_dsl(dsl_query, sid=s_id_param)
        cached_map = self.graph_api.convert_spo_to_one_graph(table)

        nodes = cached_map[f"{passage}_{chunk_label}"].in_relations['source']
        for node in nodes:
            node_dict = node.from_entity.prop.origin_prop_map
            matched_atomic_quesrions.append({
                "question":node_dict['name'],
                "answer":node_dict['answer']
            })
        return matched_atomic_quesrions


    @retry(stop=stop_after_attempt(3))
    def named_entity_recognition(self, passage: str):
        """
        Performs named entity recognition on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the named entity recognition operation.
        """
        ner_result = self.llm.invoke(
            {"input": passage}, self.ner_prompt, with_except=False
        )
        output = []
        dedup = set()
        for item in ner_result:
            name = item.get("name", None)
            if name and name not in dedup:
                dedup.add(name)
                output.append(item)
        return output

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
            {"input": passage, "named_entities": entities},
            self.std_prompt,
            with_except=False,
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
            {"input": passage, "entity_list": entities},
            self.triple_prompt,
            with_except=False,
        )

    def assemble_sub_graph_with_spg_records(self, sub_graph,entities: List[Dict]):
        """
        Assembles a subgraph using SPG records.

        Args:
            entities (List[Dict]): A list of entities to be used for subgraph assembly.

        Returns:
            The assembled subgraph and the updated list of entities.
        """
        for record in entities:
            s_name = record.get("name", "")
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
        return entities


    @staticmethod
    def assemble_sub_graph_with_AtomicQuestion(sub_graph: SubGraph, atomic_question: Dict):
        """
        Associates a Chunk object with the subgraph, adding it as a node and connecting it with existing nodes.
        Args:
            sub_graph (SubGraph): The subgraph to add the chunk information to.
            chunk (Chunk): The chunk object containing the text and metadata.
        Returns:
            The constructed subgraph.
        """
        for node in sub_graph.nodes:
            sub_graph.add_edge(node.id, node.label, "source", atomic_question['question'], 'AtomicQuestion')
        sub_graph.add_node(
            atomic_question['question'],
            atomic_question['question'],
            "AtomicQuestion",
            {
                "id": atomic_question['question'],
                "name": atomic_question['question'],
                "content": f"{atomic_question['question']}",
                "answer": atomic_question['answer']
            },
        )
        sub_graph.id = atomic_question['question']
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

        def get_category(entities_data, entity_name):
            for entity in entities_data:
                if entity["name"] == entity_name:
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

    def assemble_sub_graph(
            self,
            sub_graph: SubGraph,
            atomic_question: Dict,
            entities: List[Dict],
            triples: List[list],
    ):
        """
        Integrates entity and triple information into a subgraph, and associates it with a chunk of text.
        Args:
            chunk (Chunk): The chunk of text the subgraph is about.
            atomic_questions (List[Dict]): A list of entities identified in the chunk.
        Returns:
            The constructed subgraph.
        """

        self.assemble_sub_graph_with_entities(sub_graph, entities)
        self.assemble_sub_graph_with_triples(sub_graph, entities, triples)
        self.assemble_sub_graph_with_AtomicQuestion(sub_graph, atomic_question)
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
        atomic_questions = self.get_atomic_questions(input.id)
        for aq in atomic_questions:
            entities =  []
            triples = []
            sub_graph = SubGraph([], [])

            aq_chunk = f"{aq.get('question')} Answer:{aq.get('answer')}"
            aq_entities = self.named_entity_recognition(aq_chunk)
            aq_entities = self.assemble_sub_graph_with_spg_records(sub_graph,aq_entities)
            filtered_entities = [
                {k: v for k, v in ent.items() if k in ["name", "category"]}
                for ent in aq_entities
            ]
            triples.extend(self.triples_extraction(aq_chunk, filtered_entities))
            std_entities = self.named_entity_standardization(aq_chunk, filtered_entities)
            self.append_official_name(aq_entities, std_entities)
            entities.extend(aq_entities)

            self.assemble_sub_graph(sub_graph, aq, entities, triples)
            out.append(sub_graph)
        return out
