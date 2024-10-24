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
import json
from collections import defaultdict
from typing import List, Type, Dict

from kag.interface.builder.mapping_abc import MappingABC
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import OTHER_TYPE


class SPOMapping(MappingABC):

    def __init__(self):
        super().__init__()
        self.s_type_col = None
        self.s_id_col = None
        self.p_type_col = None
        self.o_type_col = None
        self.o_id_col = None
        self.sub_property_mapping = defaultdict(list)
        self.sub_property_col = None

    @property
    def input_types(self) -> Type[Input]:
        return Dict[str, str]

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def add_field_mappings(self, s_id_col: str, p_type_col: str, o_id_col: str, s_type_col: str = None, o_type_col: str = None):
        self.s_type_col = s_type_col
        self.s_id_col = s_id_col
        self.p_type_col = p_type_col
        self.o_type_col = o_type_col
        self.o_id_col = o_id_col
        return self

    def add_sub_property_mapping(self, source_name: str, target_name: str = None):
        """
        Adds a field mapping from source data to a property of the subject type.

        Args:
            source_name (str): The source field to be mapped.
            target_name (str): The target field to map the source field to.

        Returns:
            self
        """
        if self.sub_property_col:
            raise ValueError("Fail to add sub property mapping.")
        if not target_name:
            self.sub_property_col = source_name
        else:
            self.sub_property_mapping[target_name].append(source_name)
        return self

    def assemble_sub_graph(self, record: Dict[str, str]):
        """
        Assembles a subgraph from the provided record.

        Args:
            record (Dict[str, str]): The record containing the data to assemble into a subgraph.

        Returns:
            SubGraph: The assembled subgraph.
        """
        sub_graph = SubGraph(nodes=[], edges=[])
        s_type = record.get(self.s_type_col) or OTHER_TYPE
        s_id = record.get(self.s_id_col) or ""
        p = record.get(self.p_type_col) or ""
        o_type = record.get(self.o_type_col) or OTHER_TYPE
        o_id = record.get(self.o_id_col) or ""
        sub_graph.add_node(id=s_id, name=s_id, label=s_type)
        sub_graph.add_node(id=o_id, name=o_id, label=o_type)
        sub_properties = {}
        if self.sub_property_col:
            sub_properties = json.loads(record.get(self.sub_property_col, '{}'))
            sub_properties = {k: str(v) for k, v in sub_properties.items()}
        else:
            for target_name, source_names in self.sub_property_mapping.items():
                for source_name in source_names:
                    value = record.get(source_name)
                    sub_properties[target_name] = value
        sub_graph.add_edge(s_id=s_id, s_label=s_type, p=p, o_id=o_id, o_label=o_type, properties=sub_properties)
        return sub_graph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the mapping process on the given input and returns the resulting sub-graphs.

        Args:
            input (Input): The input data to be processed.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of resulting sub-graphs.
        """
        record: Dict[str, str] = input
        sub_graph = self.assemble_sub_graph(record)
        return [sub_graph]
