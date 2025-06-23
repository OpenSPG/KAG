from models.base import BasicInfo, SPGOntologyEnum
from models.entity import EntityType, Property, Relation, EntityInstance
from core.linking import RecordLinking, SearchBasedLinking
from core.builder import EntityBuilder
from core.neo4j_store import Neo4jStore

class MockSearchClient:
    def __init__(self):
        self.data = {
            "ENTITY": {
                "company": {"alibaba": "ali001", "tencent": "tenc001"},
                "person": {"jack ma": "p001", "pony ma": "p002"}
            }
        }
    
    def search(self, object_type: str, value: str) -> str:
        type_data = self.data.get(object_type, {})
        for entity_type, entities in type_data.items():
            if value.lower() in entities:
                return entities[value.lower()]
        return value

def create_company_type() -> EntityType:
    """创建公司实体类型"""
    return EntityType(
        basic_info=BasicInfo(
            name="Company",
            description="公司实体"
        ),
        properties=[
            Property(name="name", value_type="string")
        ]
    )

def create_person_type() -> EntityType:
    """创建人员实体类型"""
    return EntityType(
        basic_info=BasicInfo(
            name="Person",
            description="人员实体"
        ),
        properties=[
            Property(name="name", value_type="string"),
            Property(name="age", value_type="int"),
            Property(name="company", value_type="string")
        ],
        relations=[
            Relation(
                name="WORKS_AT",
                target_type="Company",
                properties=[
                    Property(name="position", value_type="string"),
                    Property(name="start_date", value_type="date")
                ]
            )
        ]
    )

def create_company_entity(company_data: dict) -> EntityInstance:
    """创建公司实体"""
    return EntityInstance(
        id=company_data["id"],
        type_name="Company",
        properties={"name": company_data["name"]}
    )

def create_test_data():
    """创建测试数据"""
    return {
        "companies": [
            {
                "id": "ali001",
                "name": "Alibaba",
                "type": "Company"
            },
            {
                "id": "tenc001",
                "name": "Tencent",
                "type": "Company"
            }
        ],
        "persons": [
            {
                "id": "person_1",
                "name": "Jack Ma",
                "age": 58,
                "company": "alibaba",
                "WORKS_AT": {  
                    "id": "ali001",
                    "position": "Founder",
                    "start_date": "1999-01-01"
                }
            },
            {
                "id": "person_2",
                "name": "Pony Ma",
                "age": 52,
                "company": "tencent",
                "WORKS_AT": {  
                    "id": "tenc001",
                    "position": "CEO",
                    "start_date": "1998-01-01"
                }
            },
            {
                "id": "person_3",
                "name": "Tom Ma",
                "age": 50,
                "company": "alibaba",
                "WORKS_AT": {  
                    "id": "ali001",
                    "position": "worker",
                    "start_date": "1998-01-01"
                }
            }
        ]
    }

def main():
    # 创建Neo4j存储
    neo4j_store = Neo4jStore(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4j@openspg"
    )

    try:
        # 创建必要的索引
        neo4j_store.create_indexes()

        # 创建搜索客户端
        search_client = MockSearchClient()
        
        # 创建实体类型
        person_type = create_person_type()
        
        # 创建链接处理器
        record_linking = RecordLinking()
        company_linking = SearchBasedLinking(search_client)

        record_linking.register_linking("company", company_linking)
        record_linking.register_linking("WORKS_AT", company_linking)
        
        # 创建实体构建器
        builder = EntityBuilder(person_type, record_linking)
        
        # 构建并存储实体
        test_data = create_test_data()

        # 首先创建公司实体
        print("\n创建公司实体:")
        for company_data in test_data["companies"]:
            company_entity = create_company_entity(company_data)
            neo4j_store.store_entity(company_entity)
            print(f"- 已创建公司: {company_data['name']} (ID: {company_data['id']})")
        
        # 然后创建人员实体及其关系
        print("\n创建人员实体:")
        for person_data in test_data["persons"]:
            entity = builder.build(person_data)
            neo4j_store.store_entity(entity)
            print(f"- 已创建人员: {person_data['name']} (ID: {person_data['id']})")

        print("\n1. 通过公司属性搜索实体:")
        alibaba_employees = neo4j_store.search_by_property("company", "ali001")
        for node in alibaba_employees:
            entity = neo4j_store.convert_to_entity_instance(node)
            print(f"- {entity.properties['name']} (ID: {entity.id})")
        
        print("\n2. 通过works_at关系搜索实体:")
        tencent_employees = neo4j_store.search_by_relation("WORKS_AT", "tenc001")
        for node in tencent_employees:
            entity = neo4j_store.convert_to_entity_instance(node)
            print(f"- {entity.properties['name']} (ID: {entity.id})")
        
        print("\n3. 搜索与特定实体相关的实体:")
        related_to_jack = neo4j_store.search_related_entities("person_1", "WORKS_AT")
        print("与Jack Ma工作相关的实体:")
        for node in related_to_jack:
            entity = neo4j_store.convert_to_entity_instance(node)
            print(f"- ID: {entity.id}")

        print("\n4. 通过关系路径搜索:")
        # 例如：查找某人所在公司的所有员工
        path_results = neo4j_store.search_by_path("person_1", ["WORKS_AT", "WORKS_AT"])
        print("与Jack Ma在同一公司的员工:")
        for node in path_results:
            entity = neo4j_store.convert_to_entity_instance(node)
            print(f"- {entity.properties['name']} (ID: {entity.id})")

    finally:
        neo4j_store.close()

if __name__ == "__main__":
    main()