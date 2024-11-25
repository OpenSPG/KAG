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
import hashlib
import pprint
from typing import Dict, List, Type, Any

from kag.schema.client import BASIC_TYPES
from kag.builder.model.spg_record import SPGRecord
from kag.schema.model.base import BaseSpgType, SpgTypeEnum


class Node(object):
    id: str
    name: str
    label: str
    properties: Dict[str, str]
    hash_map: Dict[int, str] = dict()

    def __init__(self, _id: str, name: str, label: str, properties: Dict[str, str]):
        self.name = name
        self.label = label
        self.properties = properties
        self.id = _id

    @classmethod
    def from_spg_record(cls, idx, spg_record: SPGRecord):
        return cls(
            _id=idx,
            name=spg_record.get_property("name"),
            label=spg_record.spg_type_name,
            properties=spg_record.properties,
        )

    @staticmethod
    def unique_key(spg_record):
        return spg_record.spg_type_name + '_' + spg_record.get_property("name", "")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, input: Dict):
        return cls(
            _id=input["id"],
            name=input["name"],
            label=input["label"],
            properties=input["properties"],
        )

    def __eq__(self, other):
        return self.name == other.name and self.label == other.label and self.properties == other.properties


class Edge(object):
    id: str
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    label: str
    properties: Dict[str, str]

    def __init__(
            self, _id: str, from_node: Node, to_node: Node, label: str, properties: Dict[str, str]
    ):
        self.from_id = from_node.id
        self.from_type = from_node.label
        self.to_id = to_node.id
        self.to_type = to_node.label
        self.label = label
        self.properties = properties
        if not _id:
            _id = id(self)
        self.id = _id

    @classmethod
    def from_spg_record(
            cls, s_idx, subject_record: SPGRecord, o_idx, object_record: SPGRecord, label: str
    ):
        from_node = Node.from_spg_record(s_idx, subject_record)
        to_node = Node.from_spg_record(o_idx, object_record)

        return cls(_id="", from_node=from_node, to_node=to_node, label=label, properties={})

    def to_dict(self):
        return {
            "id": self.id,
            "from": self.from_id,
            "to": self.to_id,
            "fromType": self.from_type,
            "toType": self.to_type,
            "label": self.label,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, input: Dict):
        return cls(
            _id=input["id"],
            from_node=Node(_id=input["from"], name=input["from"],label=input["fromType"], properties={}),
            to_node=Node(_id=input["to"], name=input["to"], label=input["toType"], properties={}),
            label=input["label"],
            properties=input["properties"],
        )

    def __eq__(self, other):
        return self.from_id == other.from_id and self.to_id == other.to_id and self.label == other.label and self.properties == other.properties and self.from_type == other.from_type and self.to_type == other.to_type


class SubGraph(object):
    id: str
    nodes: List[Node] = list()
    edges: List[Edge] = list()

    def __init__(self, nodes: List[Node], edges: List[Edge]):
        self.nodes = nodes
        self.edges = edges

    def add_node(self, id: str, name: str, label: str, properties={}):
        self.nodes.append(Node(_id=id, name=name, label=label, properties=properties))
        return self

    def add_edge(self, s_id: str, s_label: str, p: str, o_id: str, o_label: str, properties={}):
        s_node = Node(_id=s_id, name=s_id, label=s_label, properties={})
        o_node = Node(_id=o_id, name=o_id, label=o_label, properties={})
        self.edges.append(Edge(_id="", from_node=s_node, to_node=o_node, label=p, properties=properties))
        return self

    def to_dict(self):
        return {
            "resultNodes": [n.to_dict() for n in self.nodes],
            "resultEdges": [e.to_dict() for e in self.edges],
        }

    def __repr__(self):
        return pprint.pformat(self.to_dict())

    def update(self, sub_graph: Type['SubGraph']):
        self.nodes.extend(sub_graph.nodes)
        self.edges.extend(sub_graph.edges)

    @staticmethod
    def filter_record(spg_record: SPGRecord, spg_type: BaseSpgType):

        filtered_properties, filtered_relations = {}, {}
        for prop_name, prop_value in spg_record.properties.items():
            if prop_value != 'NAN':
                filtered_properties[prop_name] = prop_value
        for rel_name, rel_value in spg_record.relations.items():
            if rel_value != 'NAN':
                filtered_relations[rel_name] = rel_value
        spg_record.properties = filtered_properties
        spg_record.relations = filtered_relations

        # if len(spg_record.properties) == 1 and spg_record.get_property("name"):
        #     print("filtered_entity: ")
        #     print(spg_record)
        #     return None
        if spg_type.spg_type_enum == SpgTypeEnum.Event and \
                (spg_type.properties.get('subject') and not spg_record.properties.get('subject')) and \
                (spg_type.properties.get('object') and not spg_record.properties.get('object')) and \
                (spg_type.properties.get('eventTime') and not spg_record.properties.get('eventTime')):
            print("filtered_event: ")
            print(spg_record)
            return None
        else:
            return spg_record

    @staticmethod
    def filter_node(nodes: List[Node], edges: List[Edge]):
        ids = []
        filtered_nodes = []
        for edge in edges:
            ids.extend([edge.from_id, edge.to_id])
        for node in nodes:
            if len(node.properties) == 1 and node.properties.get("name"):
                if node.id not in ids:
                    print("filtered_node: ")
                    print(node)
                    continue
            filtered_nodes.append(node)
        return filtered_nodes

    @staticmethod
    def generate_hash_id(value):
        m = hashlib.md5()
        m.update(value.encode('utf-8'))
        md5_hex = m.hexdigest()
        decimal_value = int(md5_hex, 16)
        return int(str(decimal_value)[:10])

    @classmethod
    def from_spg_record(
        cls, spg_types: Dict[str, BaseSpgType], spg_records: List[SPGRecord]
    ):
        sub_graph = cls([], [])
        for record in spg_records:
            s_id = record.id
            s_name = record.name
            s_label = record.spg_type_name.split('.')[-1]
            properties = record.properties

            spg_type = spg_types.get(record.spg_type_name)
            for prop_name, prop_value in record.properties.items():
                if prop_name in spg_type.properties:
                    from kag.schema.model.property import Property
                    prop: Property = spg_type.properties.get(prop_name)
                    o_label = prop.object_type_name.split('.')[-1]
                    if o_label not in BASIC_TYPES:
                        prop_value_list = prop_value.split(',')
                        for o_id in prop_value_list:
                            sub_graph.add_edge(s_id=s_id, s_label=s_label, p=prop_name, o_id=o_id, o_label=o_label)
                        properties.pop(prop_name)
            sub_graph.add_node(id=s_id, name=s_name, label=s_label, properties=properties)

        return sub_graph

    @classmethod
    def from_dict(cls, input: Dict[str, Any]):
        return cls(
            nodes=[Node.from_dict(node) for node in input["resultNodes"]],
            edges=[Edge.from_dict(edge) for edge in input["resultEdges"]],
        )
