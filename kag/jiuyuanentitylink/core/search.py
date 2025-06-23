from typing import Dict, List, Optional, Any
from models.entity import EntityInstance, RelationInstance

class EntityIndex:
    def __init__(self):
        # 存储实体ID到实体实例的映射
        self.id_to_entity: Dict[str, EntityInstance] = {}
        # 存储属性值到实体ID的映射
        self.property_to_ids: Dict[str, Dict[str, List[str]]] = {}
        # 存储关系到实体ID的映射
        self.relation_to_ids: Dict[str, Dict[str, List[str]]] = {}

    def index_entity(self, entity: EntityInstance):
        """索引一个实体及其所有属性和关系"""
        # 存储实体本身
        self.id_to_entity[entity.id] = entity

        # 索引实体的属性
        for prop_name, prop_value in entity.properties.items():
            if prop_name not in self.property_to_ids:
                self.property_to_ids[prop_name] = {}
            if str(prop_value) not in self.property_to_ids[prop_name]:
                self.property_to_ids[prop_name][str(prop_value)] = []
            self.property_to_ids[prop_name][str(prop_value)].append(entity.id)

        # 索引实体的关系
        for relation in entity.relations:
            if relation.relation_type not in self.relation_to_ids:
                self.relation_to_ids[relation.relation_type] = {}
            if relation.dst_id not in self.relation_to_ids[relation.relation_type]:
                self.relation_to_ids[relation.relation_type][relation.dst_id] = []
            self.relation_to_ids[relation.relation_type][relation.dst_id].append(entity.id)

class EntitySearch:
    def __init__(self, entity_index: EntityIndex):
        self.index = entity_index

    def search_by_property(self, property_name: str, property_value: str) -> List[EntityInstance]:
        """通过属性值搜索实体"""
        if property_name not in self.index.property_to_ids:
            return []
        
        entity_ids = self.index.property_to_ids[property_name].get(str(property_value), [])
        return [self.index.id_to_entity[entity_id] for entity_id in entity_ids]

    def search_by_relation(self, relation_type: str, target_id: str) -> List[EntityInstance]:
        """通过关系搜索实体"""
        if relation_type not in self.index.relation_to_ids:
            return []
        
        entity_ids = self.index.relation_to_ids[relation_type].get(target_id, [])
        return [self.index.id_to_entity[entity_id] for entity_id in entity_ids]

    def search_related_entities(self, entity_id: str, relation_type: str) -> List[EntityInstance]:
        """搜索与指定实体有特定关系的所有实体"""
        if entity_id not in self.index.id_to_entity:
            return []
        
        entity = self.index.id_to_entity[entity_id]
        related_ids = []
        
        # 查找正向关系
        for relation in entity.relations:
            if relation.relation_type == relation_type:
                related_ids.append(relation.dst_id)
        
        # 查找反向关系（通过关系索引）
        if relation_type in self.index.relation_to_ids:
            reverse_ids = self.index.relation_to_ids[relation_type].get(entity_id, [])
            related_ids.extend(reverse_ids)
        
        return [self.index.id_to_entity[rid] for rid in related_ids if rid in self.index.id_to_entity]

    def search_by_path(self, start_id: str, relation_path: List[str]) -> List[EntityInstance]:
        """通过关系路径搜索实体"""
        current_entities = [self.index.id_to_entity[start_id]] if start_id in self.index.id_to_entity else []
        
        for relation_type in relation_path:
            next_entities = []
            for entity in current_entities:
                related = self.search_related_entities(entity.id, relation_type)
                next_entities.extend(related)
            current_entities = next_entities
            
        return current_entities