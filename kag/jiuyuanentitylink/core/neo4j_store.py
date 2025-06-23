from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase
from models.entity import EntityInstance, RelationInstance

class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str):
        """初始化Neo4j连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """关闭Neo4j连接"""
        self.driver.close()

    def create_indexes(self):
        """创建必要的索引"""
        with self.driver.session() as session:
            # 为实体ID创建索引
            session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)")
            # 为实体类型创建索引
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)")
            # 为属性值创建索引
            session.run("CREATE INDEX property_value IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            session.run("CREATE INDEX property_value IF NOT EXISTS FOR (n:Entity) ON (n.company)")

    def store_entity(self, entity: EntityInstance):
        """存储实体及其关系到Neo4j"""
        with self.driver.session() as session:
            # 创建实体节点
            properties = {
                "id": entity.id,
                "type": entity.type_name,
                **entity.properties
            }
            create_node_query = (
                "MERGE (n:Entity {id: $id}) "
                "SET n += $properties"
            )
            session.run(create_node_query, id=entity.id, properties=properties)

            # 创建关系
            for relation in entity.relations:
                create_relation_query = (
                    "MATCH (src:Entity {id: $src_id}), (dst:Entity {id: $dst_id}) "
                    "MERGE (src)-[r:" + relation.relation_type + "]->(dst) "
                    "SET r += $properties"
                )
                session.run(
                    create_relation_query,
                    src_id=relation.src_id,
                    dst_id=relation.dst_id,
                    properties=relation.properties
                )

    def search_by_property(self, property_name: str, property_value: str) -> List[Dict[str, Any]]:
        """通过属性值搜索实体"""
        with self.driver.session() as session:
            query = (
                f"MATCH (n:Entity) "
                f"WHERE n.{property_name} = $value "
                f"RETURN n"
            )
            result = session.run(query, value=property_value)
            return [record["n"] for record in result]

    def search_by_relation(self, relation_type: str, target_id: str) -> List[Dict[str, Any]]:
        """通过关系搜索实体"""
        with self.driver.session() as session:
            query = (
                f"MATCH (src:Entity)-[r:{relation_type}]->(dst:Entity {{id: $target_id}}) "
                f"RETURN src"
            )
            result = session.run(query, target_id=target_id)
            return [record["src"] for record in result]

    def search_related_entities(self, entity_id: str, relation_type: str) -> List[Dict[str, Any]]:
        """搜索与指定实体有特定关系的所有实体"""
        with self.driver.session() as session:
            # 查找正向关系
            forward_query = (
                f"MATCH (src:Entity {{id: $entity_id}})-[r:{relation_type}]->(dst:Entity) "
                f"RETURN dst"
            )
            # 查找反向关系
            reverse_query = (
                f"MATCH (src:Entity)-[r:{relation_type}]->(dst:Entity {{id: $entity_id}}) "
                f"RETURN src"
            )
            
            forward_results = session.run(forward_query, entity_id=entity_id)
            reverse_results = session.run(reverse_query, entity_id=entity_id)
            
            results = []
            results.extend([record["dst"] for record in forward_results])
            results.extend([record["src"] for record in reverse_results])
            return results

    def search_by_path(self, start_id: str, relation_path: List[str]) -> List[Dict[str, Any]]:
        """通过关系路径搜索实体"""
        if not relation_path:
            return []

        with self.driver.session() as session:
            # 构建关系路径查询
            path = "".join(f"-[:{rel}]-(n{i+1}:Entity)" for i, rel in enumerate(relation_path))
            query = (
                f"MATCH (n0:Entity {{id: $start_id}}){path} "
                f"RETURN n{len(relation_path)}"
            )
            result = session.run(query, start_id=start_id)
            return [record[f"n{len(relation_path)}"] for record in result]

    def convert_to_entity_instance(self, neo4j_node: Dict[str, Any]) -> EntityInstance:
        """将Neo4j节点转换为EntityInstance"""
        properties = dict(neo4j_node)
        entity_id = properties.pop("id")
        type_name = properties.pop("type")
        
        return EntityInstance(
            id=entity_id,
            type_name=type_name,
            properties=properties
        )