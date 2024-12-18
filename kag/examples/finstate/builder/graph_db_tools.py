from neo4j import GraphDatabase

# 定义数据库连接信息
uri = "neo4j://localhost:7687"
username = "neo4j"
password = "neo4j@openspg"
# 创建数据库驱动
driver = GraphDatabase.driver(uri, auth=(username, password))


def clear_neo4j_data(db_name):
    """
    清空neo4j数据
    """

    def delete_all_nodes_and_relationships(tx):
        # 删除所有节点
        tx.run("MATCH (n) DETACH DELETE n")

    with driver.session(database=db_name) as session:
        session.execute_write(delete_all_nodes_and_relationships)
