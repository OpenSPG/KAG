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

from typing import Dict, List

from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from kag.interface import MappingABC


@MappingABC.register("relation")
@MappingABC.register("relation_mapping")
class RelationMapping(MappingABC):
    """
    A class that extends the MappingABC class.
    It handles relation mappings by assembling subgraphs based on given subject, predicate, and object names.
    """

    def __init__(
        self,
        subject_name: str,
        predicate_name: str,
        object_name: str,
        src_id_field: str = None,
        dst_id_field: str = None,
        property_mapping: dict = {},
        **kwargs,
    ):
        """
        Initializes the RelationMapping instance.

        Args:
            subject_name (str): The name of the subject type.
            predicate_name (str): The name of the predicate type.
            object_name (str): The name of the object type.
            src_id_field (str, optional): The field name for the source ID. Defaults to None.
            dst_id_field (str, optional): The field name for the destination ID. Defaults to None.
            property_mapping (dict, optional): A dictionary mapping properties. Defaults to {}.
            **kwargs: Additional keyword arguments passed to the parent class constructor.
        """
        super().__init__(**kwargs)
        schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
        assert subject_name in schema, f"{subject_name} is not a valid SPG type name"
        assert object_name in schema, f"{object_name} is not a valid SPG type name"
        self.subject_type = schema.get(subject_name)
        self.object_type = schema.get(object_name)

        assert predicate_name in self.subject_type.properties or predicate_name in set(
            [key.split("_")[0] for key in self.subject_type.relations.keys()]
        ), f"{predicate_name} is not a valid SPG property/relation name"
        self.predicate_name = predicate_name

        self.src_id_field = src_id_field
        self.dst_id_field = dst_id_field
        self.property_mapping = property_mapping

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

        self.property_mapping[target_name] = source_name
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
            for target_name, source_name in self.property_mapping.items():
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

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
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
