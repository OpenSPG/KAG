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
from typing import List, Dict

from tenacity import retry, stop_after_attempt

from kag.builder.component.extractor import KAGExtractor
from kag.builder.model.sub_graph import SubGraph
from kag.builder.prompt.spg_prompt import SPG_KGPrompt
from kag.common.base.prompt_op import PromptOp
from knext.common.base.runnable import Input, Output

from knext.schema.client import BASIC_TYPES

logger = logging.getLogger(__name__)


class SPGExtractor(KAGExtractor):
    """
    A Builder Component that extracting structured data from long texts by invoking large language model.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spg_ner_types, self.kag_ner_types = [], []
        for type_name, spg_type in self.schema.items():
            properties = list(spg_type.properties.keys())
            for p in properties:
                if p not in SPG_KGPrompt.ignored_properties:
                    self.spg_ner_types.append(type_name)
                    continue
            self.kag_ner_types.append(type_name)
        self.kag_ner_prompt = PromptOp.load(self.biz_scene, "ner")(language=self.language, project_id=self.project_id)
        self.spg_ner_prompt = SPG_KGPrompt(self.spg_ner_types, self.language, project_id=self.project_id)

    @retry(stop=stop_after_attempt(3))
    def named_entity_recognition(self, passage: str):
        """
        Performs named entity recognition on a given text passage.
        Args:
            passage (str): The text to perform named entity recognition on.
        Returns:
            The result of the named entity recognition operation.
        """
        spg_ner_result = self.llm.batch({"input": passage}, self.spg_ner_prompt)
        kag_ner_result = self.llm.invoke({"input": passage}, self.kag_ner_prompt)
        return spg_ner_result + kag_ner_result

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
                            sub_graph.add_edge(s_id=s_name, s_label=s_label, p=prop_name, o_id=o_name, o_label=o_label)
                        tmp_properties.pop(prop_name)
            record["properties"] = tmp_properties
            sub_graph.add_node(id=s_name, name=s_name, label=s_label, properties=properties)
        return sub_graph, entities

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
        passage = title + "\n" + input.content

        try:
            entities = self.named_entity_recognition(passage)
            sub_graph, entities = self.assemble_sub_graph_with_spg_records(entities)
            filtered_entities = [{k: v for k, v in ent.items() if k in ["entity", "category"]} for ent in entities]
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
