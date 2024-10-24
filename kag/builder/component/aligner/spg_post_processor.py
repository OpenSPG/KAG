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

from typing import List, Type, Dict

from kag.interface.builder import AlignerABC
from knext.schema.client import BASIC_TYPES
from kag.builder.model.spg_record import SPGRecord
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from knext.schema.model.base import ConstraintTypeEnum, BaseSpgType


class SPGPostProcessorAligner(AlignerABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spg_types = SchemaClient(project_id=self.project_id).load()

    @property
    def input_types(self) -> Type[Input]:
        return SPGRecord

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def merge(self, spg_records: List[SPGRecord]):
        merged_spg_records = {}
        for record in spg_records:
            key = f"{record.spg_type_name}#{record.get_property('name', '')}"
            if key not in merged_spg_records:
                merged_spg_records[key] = record
            else:
                old_record = merged_spg_records[key]
                for prop_name, prop_value in record.properties.items():
                    if prop_name not in old_record.properties:
                        old_record.properties[prop_name] = prop_value
                    else:
                        prop = self.spg_types.get(record.spg_type_name).properties.get(
                            prop_name
                        )
                        if not prop:
                            continue
                        if (
                            prop.object_type_name not in BASIC_TYPES
                            or prop.constraint.get(ConstraintTypeEnum.MultiValue)
                        ):
                            old_value = old_record.properties.get(prop_name)
                            if not prop_value:
                                prop_value = ""
                            prop_value_list = (
                                prop_value + "," + old_value
                                if old_value
                                else prop_value
                            ).split(",")
                            old_record.properties[prop_name] = ",".join(
                                list(set(prop_value_list))
                            )
                        else:
                            old_record.properties[prop_name] = prop_value

        return list(merged_spg_records.values())

    @staticmethod
    def from_spg_record(
        spg_types: Dict[str, BaseSpgType], spg_records: List[SPGRecord]
    ):
        sub_graph = SubGraph([], [])
        for record in spg_records:
            s_id = record.id
            s_name = record.name
            s_label = record.spg_type_name
            properties = record.properties

            spg_type = spg_types.get(record.spg_type_name)
            for prop_name, prop_value in record.properties.items():
                if prop_name in spg_type.properties:
                    from knext.schema.model.property import Property

                    prop: Property = spg_type.properties.get(prop_name)
                    o_label = prop.object_type_name
                    if o_label not in BASIC_TYPES:
                        prop_value_list = prop_value.split(",")
                        for o_id in prop_value_list:
                            sub_graph.add_edge(
                                s_id=s_id,
                                s_label=s_label,
                                p=prop_name,
                                o_id=o_id,
                                o_label=o_label,
                            )
                        properties.pop(prop_name)
            sub_graph.add_node(
                id=s_id, name=s_name, label=s_label, properties=properties
            )

        return sub_graph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        subgraph = SubGraph.from_spg_record(self.spg_types, [input])
        return [subgraph]

    def batch(self, inputs: List[Input], **kwargs) -> List[Output]:
        merged_records = self.merge(inputs)
        subgraph = SubGraph.from_spg_record(self.spg_types, merged_records)
        return [subgraph]
