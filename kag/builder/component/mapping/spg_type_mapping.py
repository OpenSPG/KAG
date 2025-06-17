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
from typing import Dict, List, Callable

import pandas
from tenacity import retry, stop_after_attempt, wait_exponential
from knext.schema.client import BASIC_TYPES
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from knext.schema.model.base import SpgTypeEnum
from knext.schema.model.schema_helper import (
    PropertyName,
)
from kag.interface.builder.mapping_abc import MappingABC
from kag.common.registry import Functor


@MappingABC.register("spg")
@MappingABC.register("spg_mapping")
class SPGTypeMapping(MappingABC):
    """
    A class for mapping SPG(Semantic-enhanced Programmable Graph) types and handling their properties and strategies.

    Attributes:
        spg_type_name (SPGTypeName): The name of the SPG type.
        fuse_func (FuseOpABC, optional): The user-defined fuse operator. Defaults to None.
    """

    def __init__(
        self,
        spg_type_name: str,
        fuse_func: Functor = None,
        property_mapping: Dict = None,
        **kwargs,
    ):
        if property_mapping is None:
            property_mapping = {}
        super().__init__(**kwargs)
        self.init_schema(spg_type_name)
        self.spg_type = self.schema.get(spg_type_name)

        self.property_mapping = property_mapping
        self.link_funcs: Dict = dict()
        self.fuse_func = fuse_func

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def init_schema(self, spg_type_name):
        self.schema = SchemaClient(
            host_addr=self.kag_project_config.host_addr,
            project_id=self.kag_project_config.project_id,
        ).load()
        assert (
            spg_type_name in self.schema
        ), f"SPG type [{spg_type_name}] does not exist."

    def add_property_mapping(
        self,
        source_name: str,
        target_name: PropertyName,
        link_func: Callable = None,
    ):
        """
        Adds a property mapping from a source name to a target name within the SPG type.

        Args:
            source_name (str): The source name of the property.
            target_name (PropertyName): The target name of the property within the SPG type.
            link_func (LinkFunc, optional): The user-defined link operator. Defaults to None.

        Returns:
            self
        """
        if (
            target_name not in ["id", "name"]
            and target_name not in self.spg_type.properties
        ):
            raise ValueError(
                f"Property [{target_name}] does not exist in [{self.spg_type.name}]."
            )

        self.property_mapping[target_name] = source_name
        if link_func is not None:
            self.link_funcs[target_name] = link_func
        return self

    @property
    def input_types(self) -> Input:
        return Dict[str, str]

    @property
    def output_types(self) -> Output:
        return SubGraph

    def field_mapping(self, record: Dict[str, str]) -> Dict[str, str]:
        """
        Maps fields from a record based on the defined property mappings.

        Args:
            record (Dict[str, str]): The input record containing source names and values.

        Returns:
            Dict[str, str]: A mapped record with target names and corresponding values.
        """
        mapped_record = {}
        for target_name, source_name in self.property_mapping.items():
            value = record.get(source_name)
            mapped_record[target_name] = value
        return mapped_record

    def assemble_sub_graph(self, properties: Dict[str, str]):
        """
        Assembles a sub-graph based on the provided properties and linking strategies.

        Args:
            properties (Dict[str, str]): The properties to be used for assembling the sub-graph.

        Returns:
            SubGraph: The assembled sub-graph.
        """
        sub_graph = SubGraph(nodes=[], edges=[])
        s_id = properties.get("id", "")
        s_name = properties.get("name", s_id)
        s_label = self.spg_type.name_en

        for prop_name, prop_value in properties.items():
            if not prop_value or prop_value == pandas.NaT:
                continue
            if prop_name in self.spg_type.properties:
                prop = self.spg_type.properties.get(prop_name)
                o_label = prop.object_type_name_en
                if o_label not in BASIC_TYPES:
                    prop_value_list = prop_value.split(",")
                    for o_id in prop_value_list:
                        if prop_name in self.link_funcs:
                            link_func = self.link_funcs.get(prop_name)
                            o_ids = link_func(o_id, properties)
                            for _o_id in o_ids:
                                sub_graph.add_edge(
                                    s_id=s_id,
                                    s_label=s_label,
                                    p=prop_name,
                                    o_id=_o_id,
                                    o_label=o_label,
                                )
                        else:
                            sub_graph.add_edge(
                                s_id=s_id,
                                s_label=s_label,
                                p=prop_name,
                                o_id=o_id,
                                o_label=o_label,
                            )
        if self.spg_type.spg_type_enum == SpgTypeEnum.Concept:
            self.hypernym_predicate(sub_graph, s_id)
        else:
            sub_graph.add_node(
                id=s_id, name=s_name, label=s_label, properties=properties
            )

        return sub_graph

    def hypernym_predicate(self, sub_graph: SubGraph, concept_id: str):
        """
        Adds hypernym predicates to the sub-graph based on the provided concept ID.

        Args:
            sub_graph (SubGraph): The sub-graph to which hypernym predicates will be added.
            concept_id (str): The ID of the concept.
        """
        p = getattr(self.spg_type, "hypernym_predicate") or "isA"
        label = self.spg_type.name_en
        concept_list = concept_id.split("-")

        father_id = ""
        for concept_name in concept_list:
            concept_id = father_id + "-" + concept_name if father_id else concept_name
            sub_graph.add_node(id=concept_id, name=concept_name, label=label)
            if father_id:
                sub_graph.add_edge(
                    s_id=concept_id, s_label=label, p=p, o_id=father_id, o_label=label
                )
            father_id = concept_id

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the mapping process on the given input and returns the resulting sub-graphs.

        Args:
            input (Input): The input data to be processed.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of resulting sub-graphs.
        """
        if self.property_mapping:
            properties = self.field_mapping(input)
        else:
            properties = input
        sub_graph = self.assemble_sub_graph(properties)
        return [sub_graph]
