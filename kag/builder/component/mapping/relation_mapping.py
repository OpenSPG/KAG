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

from collections import defaultdict
from typing import Dict, List

from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient

from knext.schema.model.schema_helper import (
    SPGTypeName,
    RelationName,
)
from kag.interface.builder.mapping_abc import MappingABC


class RelationMapping(MappingABC):
    """
    A class that handles relation mappings by assembling subgraphs based on given subject, predicate, and object names.
    This class extends the Mapping class.

    Args:
        subject_name (SPGTypeName): The name of the subject type.
        predicate_name (RelationName): The name of the predicate.
        object_name (SPGTypeName): The name of the object type.
    """

    def __init__(
        self,
        subject_name: SPGTypeName,
        predicate_name: RelationName,
        object_name: SPGTypeName,
        **kwargs
    ):
        super().__init__(**kwargs)
        schema = SchemaClient(project_id=self.project_id).load()
        assert subject_name in schema, f"{subject_name} is not a valid SPG type name"
        assert object_name in schema, f"{object_name} is not a valid SPG type name"
        self.subject_type = schema.get(subject_name)
        self.object_type = schema.get(object_name)

        assert predicate_name in self.subject_type.properties or predicate_name in set(
            [key.split("_")[0] for key in self.subject_type.relations.keys()]
        ), f"{predicate_name} is not a valid SPG property/relation name"
        self.predicate_name = predicate_name

        self.src_id_field = None
        self.dst_id_field = None
        self.property_mapping: Dict = defaultdict(list)
        self.linking_strategies: Dict = dict()

    def add_src_id_mapping(self, source_name: str):
        """
        Adds a field mapping from source data to the subject's ID property.

        Args:
            source_name (str): The name of the source field to map.

        Returns:
            self
        """
        self.src_id_field = source_name
        return self

    def add_dst_id_mapping(self, source_name: str):
        """
        Adds a field mapping from source data to the object's ID property.

        Args:
            source_name (str): The name of the source field to map.

        Returns:
            self
        """
        self.dst_id_field = source_name
        return self

    def add_sub_property_mapping(self, source_name: str, target_name: str):
        """
        Adds a field mapping from source data to a property of the subject type.

        Args:
            source_name (str): The source field to be mapped.
            target_name (str): The target field to map the source field to.

        Returns:
            self
        """
        self.property_mapping[target_name].append(source_name)
        return self

    @property
    def input_types(self) -> Input:
        return Dict[str, str]

    @property
    def output_types(self) -> Output:
        return SubGraph

    def assemble_sub_graph(self, record: Dict[str, str]) -> SubGraph:
        """
        Assembles a subgraph from the provided record.

        Args:
            record (Dict[str, str]): The record containing the data to assemble into a subgraph.

        Returns:
            SubGraph: The assembled subgraph.
        """
        sub_graph = SubGraph(nodes=[], edges=[])
        if self.property_mapping:
            s_id = record.get(self.src_id_field or "srcId")
            o_id = record.get(self.dst_id_field or "dstId")
            sub_properties = {}
            for target_name, source_names in self.property_mapping.items():
                for source_name in source_names:
                    value = record.get(source_name)
                    sub_properties[target_name] = value
        else:
            s_id = record.pop(self.src_id_field or "srcId")
            o_id = record.pop(self.dst_id_field or "dstId")
            sub_properties = record

        sub_graph.add_edge(
            s_id=s_id,
            s_label=self.subject_type.name_en,
            p=self.predicate_name,
            o_id=o_id,
            o_label=self.object_type.name_en,
            properties=sub_properties,
        )

        return sub_graph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the assembly process to create a subgraph from the input data.

        Args:
            input (Input): The input data to assemble into a subgraph.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list containing the assembled subgraph.
        """
        sub_graph = self.assemble_sub_graph(input)
        return [sub_graph]
