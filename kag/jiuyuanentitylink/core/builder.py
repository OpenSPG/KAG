from typing import Dict, List, Optional, Any
from models.entity import EntityType, EntityInstance, RelationInstance
from core.linking import RecordLinking

class EntityBuilder:
    def __init__(self, entity_type: EntityType, record_linking: RecordLinking):
        self.entity_type = entity_type
        self.record_linking = record_linking

    def build(self, raw_data: Dict[str, Any]) -> EntityInstance:
        """从原始数据构建实体实例"""
        # 创建实体实例
        entity = EntityInstance(
            id=raw_data.get("id"),
            type_name=self.entity_type.basic_info.name,
            properties=self._extract_properties(raw_data),
            relations=self._extract_relations(raw_data)
        )

        # 处理实体链接
        self.record_linking.linking(entity)
        return entity

    def _extract_properties(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取属性值"""
        properties = {}
        for prop in self.entity_type.properties:
            if prop.name in raw_data:
                properties[prop.name] = raw_data[prop.name]
        return properties

    def _extract_relations(self, raw_data: Dict[str, Any]) -> List[RelationInstance]:
        """提取关系"""
        relations = []
        for rel in self.entity_type.relations:
            rel_data = raw_data.get(rel.name)
            if rel_data:
                if isinstance(rel_data, list):
                    for target in rel_data:
                        relations.append(
                            RelationInstance(
                                src_id=raw_data["id"],
                                dst_id=target if isinstance(target, str) else target.get("id"),
                                relation_type=rel.name,
                                properties=target if isinstance(target, dict) else {}
                            )
                        )
                else:
                    relations.append(
                        RelationInstance(
                            src_id=raw_data["id"],
                            dst_id=rel_data if isinstance(rel_data, str) else rel_data.get("id"),
                            relation_type=rel.name,
                            properties=rel_data if isinstance(rel_data, dict) else {}
                        )
                    )
        return relations