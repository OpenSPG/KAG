import json
import os
import csv

from neo4j import GraphDatabase

# Neo4j连接配置
URI = "bolt://localhost:7687"  # 替换为你的Neo4j服务器地址
USER = "neo4j"  # 默认用户名
PASSWORD = "neo4j@openspg"  # 替换为你的密码

# 创建驱动实例
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def load_schema(db_name):
    with open(
        f"/home/zhenzhi/code/KAG/kag/examples/bird_graph/table_2_graph/bird_dev_graph_dataset/{db_name}.schema.json",
        "r",
        encoding="utf-8",
    ) as f:
        schema_info = json.load(f)
    return schema_info


def import_node(db_name, node_type, primary_key):
    print(f"start load {node_type}")
    cypher = f"""
LOAD CSV WITH HEADERS FROM 'file:///bird_dev_graph_dataset/nodes/{db_name}.{node_type}.csv' AS row
WITH apoc.map.clean(row, [], ['null', '', 'NA']) AS filteredRow
CREATE (n:{db_name}_{node_type})
    SET n += filteredRow,
        n.id = filteredRow.{primary_key};
"""
    with driver.session() as session:
        session.run(f"MATCH (n:{db_name}_{node_type}) DETACH DELETE n")
        session.run(cypher)
        session.run(
            f"CREATE CONSTRAINT FOR (n:{db_name}_{node_type}) REQUIRE n.id IS UNIQUE;"
        )
    print(f"load {node_type} done")


def import_edge(db_name, s, p, o):
    print(f"start load edge {s}_{p}_{o}")
    cypher = f"""
LOAD CSV WITH HEADERS FROM 'file:///bird_dev_graph_dataset/edges/{db_name}.{s}_{p}_{o}.csv' AS row
MATCH (s:{db_name}_{s} {{id: row.s}})
MATCH (o:{db_name}_{o} {{id: row.o}})
WITH s, o, apoc.map.clean(row, ['s', 'o', 'p'], []) AS properties, row.p AS relationshipType
CALL apoc.create.relationship(s, relationshipType, properties, o) YIELD rel
RETURN rel
"""
    with driver.session() as session:
        session.run(f"MATCH ()-[r:{p}]-() DELETE r")
        session.run(cypher)
    print(f"load edge {s}_{p}_{o} done")


def find_csv_files(directory, db_name):
    csv_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file: str = file
            if file.endswith(".csv") and file.startswith(db_name):
                csv_files.append(os.path.join(root, file))
    return csv_files


if __name__ == "__main__":
    _graph_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bird_dev_graph_dataset",
    )

    _all_nodes = find_csv_files(_graph_path + "/nodes", "california_schools")
    _all_edges = find_csv_files(_graph_path + "/edges", "california_schools")

    import_node("california_schools", "schools", "CDSCode")
    import_node("california_schools", "frpm", "CDSCode")
    import_edge("california_schools", "frpm", "hasSchoolDetails", "schools")
