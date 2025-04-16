#!/usr/bin/python
# coding=utf8

import csv
import json
from collections import defaultdict
from typing import List

from knext.reasoner.client import ReasonerClient
from knext.schema.model.property import Property
from kag.common.config import LogicFormConfiguration


class SchemaUtils:
    def __init__(self, config: LogicFormConfiguration):
        self.config: LogicFormConfiguration = config
        self.prefix = config.prefix
        self.prefix_concat_sign = "."
        self.project_id = config.project_id
        self.nodes = set()  # zh
        self.edges = set()  # zh
        self.spo = set()  # zh
        self.spo_en = set()  # en
        self.node_attr = {}  # {node_zh:[attr_zh]}
        self.edge_attr = {}
        self.node_edge = {}
        self.so_p = defaultdict(set)
        self.sp_o = defaultdict(set)
        self.op_s = defaultdict(set)
        self.so_p_en = defaultdict(set)
        self.sp_o_en = defaultdict(set)
        self.op_s_en = defaultdict(set)
        self.s_po_en = defaultdict(set)
        self.o_ps_en = defaultdict(set)
        self.node_zh_en = {}
        self.node_en_zh = {}
        self.node_zh_2_full_name = {}
        self.node_en_2_full_name = {}
        self.full_name_2_node_en = {}
        self.edge_zh_en = {}
        self.edge_en_zh = {}
        self.spo_zh_en = {}
        self.spo_en_zh = {}
        self.attr_zh_en = {}
        self.attr_zh_en_by_label = {}
        self.attr_en_zh = {}
        self.attr_en_zh_by_label = {}
        self.attr_enums = {}
        self.ext_attr_name_set = ["basicInfo", "infobox"]
        self.get_schema()

    def get_spo_with_p(self, spo):
        _, p, _ = spo.split("_")
        return p

    def get_label_within_prefix(self, label_name_without_prefix):
        if not label_name_without_prefix:
            return label_name_without_prefix

        if label_name_without_prefix in self.node_en_2_full_name:
            return self.node_en_2_full_name.get(label_name_without_prefix)
        if label_name_without_prefix in self.node_zh_2_full_name:
            return self.node_zh_2_full_name.get(label_name_without_prefix)
        return label_name_without_prefix

    def get_label_without_prefix(self, label_name_with_prefix):
        if not label_name_with_prefix:
            return label_name_with_prefix
        if label_name_with_prefix in self.full_name_2_node_en:
            return self.full_name_2_node_en.get(label_name_with_prefix)
        return label_name_with_prefix

    def _add_attr_with_label(self, label_name, nameZh, name):
        if label_name in self.attr_en_zh_by_label.keys():
            attr_en_zh_tmp = self.attr_en_zh_by_label[label_name]
            attr_en_zh_tmp[name] = nameZh
        else:
            attr_en_zh_tmp = {name: nameZh}
        self.attr_en_zh_by_label[label_name] = attr_en_zh_tmp

        if label_name in self.attr_zh_en_by_label.keys():
            attr_zh_en_tmp = self.attr_zh_en_by_label[label_name]
            attr_zh_en_tmp[nameZh] = name
        else:
            attr_zh_en_tmp = {nameZh: name}
        self.attr_zh_en_by_label[label_name] = attr_zh_en_tmp

    def get_attr_en_zh_by_label(self, label_name):
        if label_name not in self.attr_en_zh_by_label.keys():
            return {}
        return self.attr_en_zh_by_label[label_name]

    def get_attr_zh_en_by_label(self, label_name):
        if label_name not in self.attr_zh_en_by_label.keys():
            return {}
        return self.attr_zh_en_by_label[label_name]

    def get_attr(self, label_name, attributes):
        attributes_namezh = []
        if not attributes:
            return attributes_namezh
        for attribute in attributes:
            if not attribute:
                continue
            # print('attribute:', attribute)
            attribute = json.loads(attribute)
            if (
                "constraints" in attribute
                and "name" in attribute["constraints"]
                and attribute["constraints"]["name"] == "Enum"
            ):
                enums = list(attribute["constraints"]["value"].keys())
            else:
                enums = None
            if attribute["name"].startswith("kg") and attribute["name"].endswith("Raw"):
                continue
            self.attr_zh_en[attribute["nameZh"]] = attribute["name"]
            self.attr_en_zh[attribute["name"]] = attribute["nameZh"]
            self.attr_enums[attribute["nameZh"]] = enums
            self._add_attr_with_label(
                label_name, attribute["nameZh"], attribute["name"]
            )
            attributes_namezh.append(attribute["nameZh"])
        return attributes_namezh

    def get_ext_json_prop(self):
        return self.ext_attr_name_set

    def get_schema(self):
        if self.config.schema_file_name == "":
            return self.get_schema_from_spg()
        return self.get_schema_from_csv()

    def get_schema_from_spg(self):
        sc = ReasonerClient(self.config.host_addr, int(self.project_id))
        spg_schema = sc.get_reason_schema()
        node_attributes = {}
        for spg_type_name, spg_type in spg_schema.items():
            name_en = spg_type.name_en
            name_zh = spg_type.name_zh
            self.node_en_2_full_name[name_en] = spg_type.name
            self.full_name_2_node_en[spg_type.name] = name_en
            self.node_zh_2_full_name[name_zh] = spg_type.name
            father_en = spg_type.parent_type_name
            attributes = self._convert_spg_attr_set(list(spg_type.properties.values()))
            if father_en and father_en in node_attributes:
                attributes += node_attributes[father_en]
            node_attributes[name_en] = attributes

            self.nodes.add(name_zh)
            self.node_zh_en[name_zh] = name_en
            self.node_en_zh[name_en] = name_zh
            entity_default_attributes = [
                '{"name": "name", "nameZh": "名称"}',
                '{"name": "id", "nameZh": "实体主键"}',
                '{"name": "description", "nameZh": "描述"}',
            ]
            attributes += entity_default_attributes
            attributes_namezh = self.get_attr(name_en, attributes)
            self.node_attr[name_zh] = attributes_namezh

            relations = spg_type.relations.values()
            for relation in relations:
                s_name_en = name_en
                s_name_zh = name_zh
                p_name_en = relation.name
                p_name_zh = relation.name_zh
                if relation.object_type_name not in spg_schema:
                    continue
                spg_o_type = spg_schema[relation.object_type_name]
                o_name_en = spg_o_type.name_en
                o_name_zh = spg_o_type.name_zh
                r_name_zh = f"{s_name_zh}_{p_name_zh}_{o_name_zh}"
                r_name_en = f"{s_name_en}_{p_name_en}_{o_name_en}"

                if r_name_zh not in self.spo:
                    self.spo.add(r_name_zh)
                if r_name_en not in self.spo_en:
                    self.spo_en.add(r_name_en)

                self.spo_en_zh[r_name_en] = r_name_zh
                self.spo_zh_en[r_name_zh] = r_name_en
                self.so_p[(s_name_zh, o_name_zh)].add(p_name_zh)
                self.sp_o[(s_name_zh, p_name_zh)].add(o_name_zh)
                self.op_s[(o_name_zh, p_name_zh)].add(s_name_zh)
                self.so_p_en[(s_name_en, o_name_en)].add(p_name_en)
                self.sp_o_en[(s_name_en, p_name_en)].add(o_name_en)
                self.op_s_en[(o_name_en, p_name_en)].add(s_name_en)
                self.s_po_en[s_name_en].add((p_name_en, o_name_en))
                self.o_ps_en[o_name_en].add((p_name_en, s_name_en))
                self.edges.add(r_name_zh)
                self.edge_zh_en[r_name_zh] = r_name_en
                self.edge_en_zh[r_name_en] = r_name_zh
                if s_name_zh not in self.node_edge:
                    self.node_edge[s_name_zh] = set()
                self.node_edge[s_name_zh].add(p_name_zh)
                if o_name_zh not in self.node_edge:
                    self.node_edge[o_name_zh] = set()
                self.node_edge[o_name_zh].add(p_name_zh)
                r_attributes = self._convert_spg_attr_set(
                    list(relation.sub_properties.values())
                )
                r_attributes_namezh = self.get_attr(name_en, r_attributes)
                self.edge_attr[p_name_zh] = r_attributes_namezh

    def get_schema_from_csv(self):
        f = open(self.config.schema_file_name)

        reader = csv.reader(f)
        next(reader)
        # next(reader)
        node_attributes = {}
        for row in reader:
            obj, name_zh, name_en, father_en, _, attributes = (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[6:],
            )
            if "nodeType/edgeType" in obj:
                continue
            name_en = name_en.replace(self.prefix, "")
            # if name_en in ['Event', 'ProductTaxon']:
            if father_en and father_en in node_attributes:
                attributes += node_attributes[father_en]
            node_attributes[name_en] = attributes
            if obj not in ["edge", "inputEdge"]:
                # if name_zh in ['百科实体', '热点事件', '事件']:
                if name_zh in ["百科实体"]:
                    continue
                self.nodes.add(name_zh)
                self.node_zh_en[name_zh] = name_en
                self.node_en_zh[name_en] = name_zh
                entity_default_attributes = [
                    '{"name": "name", "nameZh": "名称"}',
                    '{"name": "id", "nameZh": "实体主键"}',
                    '{"name": "description", "nameZh": "描述"}',
                ]
                attributes += entity_default_attributes
                attributes_namezh = self.get_attr(name_en, attributes)
                self.node_attr[name_zh] = attributes_namezh

            elif obj == "edge":
                s, p, o = name_zh.split("_")
                # if s in ['百科实体', '热点事件', '事件'] or o in ['百科实体', '热点事件', '事件']:
                if s in ["百科实体"] or o in ["百科实体"]:
                    continue
                if name_zh not in self.spo:
                    self.spo.add(name_zh)
                if name_en not in self.spo_en:
                    self.spo_en.add(name_en)
                self.spo_en_zh[name_en] = name_zh
                self.spo_zh_en[name_zh] = name_en
                self.so_p[(s, o)].add(p)
                self.sp_o[(s, p)].add(o)
                self.sp_o[(o, p)].add(s)
                s_en, p_en, o_en = name_en.split("_")
                self.so_p_en[(s_en, o_en)].add(p_en)
                self.sp_o_en[(s_en, p_en)].add(o_en)
                self.op_s_en[(o_en, p_en)].add(s_en)
                self.s_po_en[s_en].add((p_en, o_en))
                self.o_ps_en[o_en].add((p_en, s_en))
                self.edges.add(p)
                self.edge_zh_en[p] = p_en
                self.edge_en_zh[p_en] = p
                if s not in self.node_edge:
                    self.node_edge[s] = set()
                self.node_edge[s].add(p)
                if o not in self.node_edge:
                    self.node_edge[o] = set()
                self.node_edge[o].add(p)
                attributes_namezh = self.get_attr(name_en, attributes)
                self.edge_attr[p] = attributes_namezh

    def get_schema_rdf(self, path_node, path_edge):
        f_node = open(path_node)
        f_edge = open(path_edge)
        for row in csv.DictReader(f_node):
            name, _ = row["name"], row["alias"]
            self.nodes.add(name)
        for row in csv.DictReader(f_edge):
            name = row["name"]
            self.edges.add(name)

    def _convert_spg_attr_set(self, attr_set: List[Property]):
        return [
            json.dumps(
                {
                    "constraints": attr.to_dict().get("constraint", {}),
                    "name": attr.to_dict().get("name"),
                    "nameZh": attr.to_dict().get("name_zh"),
                }
            )
            for attr in attr_set
        ]


def generate_nodes_edges_hetero(schema):
    """
    nodes {
        hetero {
            "CommonSenseKG.Person" {
                fe: [
                    "gender;Raw|use_fe=False;Direct;str",
                ]
            }
            "CommonSenseKG.Work" {
                fe: [
                    "releaseDate;Raw|use_fe=False;Direct;str",
                ]
            }
        }
    }
    edges {
        hetero {
            "CommonSenseKG.Person_debutWork_CommonSenseKG.Work" {
                fe: []
            }
            "CommonSenseKG.Person_representativeWork_CommonSenseKG.Work" {
                fe: []
            }
        }
    }
    """
    nodes_hetero, edges_hetero = defaultdict(dict), defaultdict(dict)
    for node in schema.nodes:
        node = schema.node_zh_en[node]
        features = []
        for attr in schema.node_attr[schema.node_en_zh[node]]:
            attr = schema.attr_zh_en[attr]
            features.append(attr + ";Raw|use_fe=False;Direct;str")
        node = schema.prefix + "." + node
        nodes_hetero[node] = {"fe": features}

    for spo in schema.spo_en:
        s, p, o = spo.split("_")
        edge = "_".join([schema.prefix + "." + s, p, schema.prefix + "." + o])
        edges_hetero[edge] = {"fe": []}

    print(
        "nodes_hetero:",
        json.dumps(nodes_hetero, indent=2).replace('"fe"', "fe").replace("},", "}"),
    )
    print(
        "edges_hetero:",
        json.dumps(edges_hetero, indent=2).replace('"fe"', "fe").replace("},", "}"),
    )
