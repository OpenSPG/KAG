from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from models.entity import EntityInstance, RelationInstance

class PropertyLinking(ABC):
    @abstractmethod
    def linking(self, record: Dict[str, Any]) -> List[str]:
        pass

class SearchBasedLinking(PropertyLinking):
    def __init__(self, search_client: Any):
        self.search_client = search_client

    def linking(self, record: Dict[str, Any]) -> List[str]:
        """基于搜索的实体链接"""
        object_type = record.get("object_type")
        raw_values = record.get("values", [])
        results = []
        for value in raw_values:
            if object_type in ["ENTITY", "CONCEPT"]:
                search_result = self.search_client.search(object_type, value)
                if search_result:
                    results.append(search_result)
            else:
                results.append(value)
        
        return results

class RecordLinking:
    def __init__(self):
        self.semantic_property_linking: Dict[str, PropertyLinking] = {}
        self.default_property_linking: PropertyLinking = None

    def register_linking(self, property_name: str, linking: PropertyLinking):
        """注册属性链接处理器"""
        self.semantic_property_linking[property_name] = linking

    def set_default_linking(self, linking: PropertyLinking):
        """设置默认链接处理器"""
        self.default_property_linking = linking

    def linking(self, entity: EntityInstance):
        """处理实体的链接"""
        # 处理属性链接
        for prop_name, prop_value in entity.properties.items():
            if prop_name in self.semantic_property_linking:
                linking = self.semantic_property_linking[prop_name]
                record = {
                    "object_type": "ENTITY",
                    "values": [prop_value] if isinstance(prop_value, str) else prop_value
                }
                linked_values = linking.linking(record)
                entity.properties[prop_name] = linked_values[0] if linked_values else prop_value
            elif self.default_property_linking:
                record = {
                    "object_type": "PROPERTY",
                    "values": [prop_value] if isinstance(prop_value, str) else prop_value
                }
                linked_values = self.default_property_linking.linking(record)
                entity.properties[prop_name] = linked_values[0] if linked_values else prop_value

        # 处理关系链接
        for relation in entity.relations:
            self._link_relation(relation)

    def _link_relation(self, relation: RelationInstance):
        """处理关系的链接"""
        # 如果目标ID在语义链接处理器中有对应的处理器，则进行处理
        if relation.relation_type in self.semantic_property_linking:
            linking = self.semantic_property_linking[relation.relation_type]
            record = {
                "object_type": "ENTITY",
                "values": [relation.dst_id]
            }
            linked_values = linking.linking(record)
            if linked_values:
                relation.dst_id = linked_values[0] 