import os
import time
from enum import Enum

import json
from typing import Any, List
import logging


logger = logging.getLogger()


class AttributeDetail:
    def __init__(self):
        self.name: str = None
        self.value: Any = None


class EntityDetail:
    def __init__(self):
        self.id: str = None
        self.entity_type_name: str = None
        self.kg_internal_id: str = None
        self.properties: List[AttributeDetail] = []

    @staticmethod
    def from_dict(json_dict):
        entity = EntityDetail()
        entity.id = json_dict["id"]
        entity.entity_type_name = json_dict["entityTypeName"]
        entity.kg_internal_id = json_dict["kgInternalId"]
        entity.properties = json_dict["properties"]
        return entity


class TableData:
    def __init__(self):
        self.header = []
        self.data = []

    @staticmethod
    def from_dict(json_dict):
        entity = TableData()
        entity.header = json_dict["header"]
        entity.data = json_dict["data"]
        return entity

class RelationDetail:
    def __init__(self):
        self.start_entity_type_name = None
        self.start_entity_kg_interanl_id = None
        self.relation_type_name = None
        self.end_entity_type_name = None
        self.end_entity_kg_interanl_id = None
        self.properties = []

    @staticmethod
    def from_dict(json_dict):
        rel = RelationDetail()
        rel.start_entity_type_name = json_dict["startEntityTypeName"]
        rel.start_entity_kg_interanl_id = json_dict["startEntityKgInteranlId"]
        rel.end_entity_kg_interanl_id = json_dict["endEntityKgInteranlId"]
        rel.end_entity_type_name = json_dict["endEntityTypeName"]

        rel.properties = json_dict["properties"]

        rel.relation_type_name = json_dict["relationTypeName"]
        return rel


class ViewLevel(str, Enum):
    GRAPH = "GRAPH"
    TABLE = "TABLE"


class GraphDetail:
    def __init__(self):
        self.nodes: List[EntityDetail] = []
        self.edges: List[RelationDetail] = []
        self.other = None
        self.next_query_id: str = None
        self.view_level: ViewLevel = ViewLevel.GRAPH
        self.tableData: TableData = None

    @staticmethod
    def from_json(json_str):
        json_obj = json.loads(json_str)
        return GraphDetail.from_dict(json_obj)

    @staticmethod
    def from_dict(json_dict):
        graph_detail = GraphDetail()
        nodes = json_dict['nodes']
        if len(nodes) != 0:
            for node in nodes:
                graph_detail.nodes.append(EntityDetail.from_dict(node))

        edges = json_dict['edges']
        if len(edges) != 0:
            for edge in edges:
                graph_detail.edges.append(RelationDetail.from_dict(edge))
        graph_detail.other = json_dict['other']
        graph_detail.next_query_id = json_dict['nextQueryId']
        graph_detail.view_level = ViewLevel[json_dict['viewLevel'].upper()]

        if "tableDetail" in json_dict.keys() and json_dict["tableDetail"] is not None:
            graph_detail.tableData = TableData.from_dict(json_dict["tableDetail"])
        return graph_detail
