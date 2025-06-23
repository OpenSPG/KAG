from models.base import BasicInfo, SPGOntologyEnum
from models.entity import EntityType, Property, Relation, EntityInstance
from core.linking import RecordLinking, SearchBasedLinking
from core.builder import EntityBuilder
from core.search import EntityIndex, EntitySearch
from typing import List

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
                name="works_at",
                target_type="Company",
                properties=[
                    Property(name="position", value_type="string"),
                    Property(name="start_date", value_type="date")
                ]
            )
        ]
    )

def create_test_data(builder: EntityBuilder) -> List[EntityInstance]:
    """创建测试数据"""
    test_data = [
        {
            "id": "person_1",
            "name": "Jack Ma",
            "age": 58,
            "company": "alibaba",
            "works_at": {
                "id": "alibaba",
                "position": "Founder",
                "start_date": "1999-01-01"
            }
        },
        {
            "id": "person_2",
            "name": "Pony Ma",
            "age": 52,
            "company": "tencent",
            "works_at": {
                "id": "tencent",
                "position": "CEO",
                "start_date": "1998-01-01"
            }
        }
    ]
    
    return [builder.build(data) for data in test_data]

def main():
    # 创建搜索客户端和索引
    search_client = MockSearchClient()
    entity_index = EntityIndex()
    
    # 创建实体类型
    person_type = create_person_type()
    
    # 创建链接处理器
    record_linking = RecordLinking()
    company_linking = SearchBasedLinking(search_client)
    record_linking.register_linking("company", company_linking)
    record_linking.register_linking("works_at", company_linking)
    
    # 创建实体构建器
    builder = EntityBuilder(person_type, record_linking)
    
    # 创建测试数据并索引
    entities = create_test_data(builder)
    for entity in entities:
        entity_index.index_entity(entity)
    
    # 创建搜索器
    entity_search = EntitySearch(entity_index)
    
    # 演示各种搜索方式
    print("\n1. 通过公司属性搜索实体:")
    alibaba_employees = entity_search.search_by_property("company", "ali001")
    for employee in alibaba_employees:
        print(f"- {employee.properties['name']} (ID: {employee.id})")
    
    print("\n2. 通过works_at关系搜索实体:")
    tencent_employees = entity_search.search_by_relation("works_at", "tenc001")
    for employee in tencent_employees:
        print(f"- {employee.properties['name']} (ID: {employee.id})")
    
    print("\n3. 搜索与特定实体相关的实体:")
    related_to_jack = entity_search.search_related_entities("person_1", "works_at")
    print("与Jack Ma工作相关的实体:")
    for related in related_to_jack:
        print(f"- ID: {related.id}")

if __name__ == "__main__":
    main()