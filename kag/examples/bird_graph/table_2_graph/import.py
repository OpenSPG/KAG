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

DATABASE = "birdgraph"


def load_schema(db_name):
    entity_map = {}
    edge_map = {}
    with open(
        f"/home/zhenzhi/code/KAG/kag/examples/bird_graph/table_2_graph/bird_dev_graph_dataset/{db_name}.schema.json",
        "r",
        encoding="utf-8",
    ) as f:
        schema_info = json.load(f)
    for info in schema_info:
        if "entity_type" in info:
            entity_map[info["entity_type"]] = info
        else:
            spo = f"{info['s']}_{info['edge_type']}_{info['o']}"
            edge_map[spo] = info
    return entity_map, edge_map


def get_type_map_from_graph_schema(db_name, entity_name):
    rst_map = {}
    entity_map, _ = load_schema(db_name)
    entity_info = entity_map[entity_name]
    pk = entity_info["pk"]
    schema = entity_info["schema"]
    for column_info in schema:
        name = column_info["column_name"]
        # if name == pk:
        #     continue
        column_type = column_info["column_type"]
        rst_map[name] = column_type
    return rst_map


def clear_graph():
    with driver.session(database=DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n;")


def import_node(db_name, node_type, primary_key, type_map):
    """
    Import nodes into the graph database.

    Parameters:
    - db_name (str): The database name.
    - node_type (str): The type of the node to import.
    - primary_key (str): The primary key field for the node.
    - type_map (dict): A dictionary mapping field names to their types (e.g., "int", "float", "string").
    """
    print(f"Start loading {node_type}")

    # Prepare Cypher SET statements for type casting
    type_casting_statements = []
    for field, field_type in type_map.items():
        field_type: str = field_type
        if field_type.lower().startswith("int"):
            type_casting_statements.append(
                f"n.`{field}` = toInteger(filteredRow.`{field}`)"
            )
        elif field_type.lower().startswith("float"):
            type_casting_statements.append(
                f"n.`{field}` = toFloat(filteredRow.`{field}`)"
            )
        elif field_type.lower() == "string":
            type_casting_statements.append(
                f"n.`{field}` = toString(filteredRow.`{field}`)"
            )
        elif field_type.lower() == "date":
            type_casting_statements.append(f"n.`{field}` = date(filteredRow.`{field}`)")
        elif field_type.lower() == "datetime":
            type_casting_statements.append(
                f"n.`{field}` = datetime(filteredRow.`{field}`)"
            )
        # Optionally handle more types here, if needed
        else:
            type_casting_statements.append(
                f"n.`{field}` = filteredRow.`{field}`"
            )  # Default: no type casting

    # Combine all SET statements into one string
    type_casting_cypher = ",\n        ".join(type_casting_statements)

    # Construct the full Cypher query
    cypher = f"""
LOAD CSV WITH HEADERS FROM 'file:///bird_dev_graph_dataset/nodes/{db_name}.{node_type}.csv' AS row
WITH apoc.map.clean(row, [], ['null', '', 'NA']) AS filteredRow
CREATE (n:{db_name}_{node_type})
    SET n.id = toString(filteredRow.`{primary_key}`),
        {type_casting_cypher}
RETURN count(n) AS node_count;
"""
    with driver.session(database=DATABASE) as session:
        result = session.run(cypher)
        record = result.single()
        loaded_count = record["node_count"] if record else 0
        session.run(
            f"CREATE CONSTRAINT {db_name}_{node_type}_id_unique IF NOT EXISTS FOR (n:{db_name}_{node_type}) REQUIRE n.id IS UNIQUE;"
        )
    print(f"Loading {node_type} done, count={loaded_count}")


def import_edge(db_name, s, p, o):
    print(f"start load edge {s}_{p}_{o}")
    cypher = f"""
LOAD CSV WITH HEADERS FROM 'file:///bird_dev_graph_dataset/edges/{db_name}.{s}_{p}_{o}.csv' AS row
MATCH (s:{db_name}_{s} {{id: row.s}})
MATCH (o:{db_name}_{o} {{id: row.o}})
WITH s, o, apoc.map.clean(row, ['s', 'o', 'p'], []) AS properties, row.p AS relationshipType
CALL apoc.create.relationship(s, relationshipType, properties, o) YIELD rel
RETURN COUNT(rel) AS edge_count
"""
    # print(cypher)
    with driver.session(database=DATABASE) as session:
        session.run(f"MATCH ()-[r:{p}]-() DELETE r")
        result = session.run(cypher)
        edge_count = result.single()["edge_count"]
    print(f"load edge {s}_{p}_{o} done, count={edge_count}")


def find_csv_files(directory, db_name):
    csv_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file: str = file
            if file.endswith(".csv") and file.startswith(db_name):
                csv_files.append(os.path.join(root, file))
    return csv_files


def get_entity_pk(entity_map, entity_name):
    info = entity_map[entity_name]
    return info["pk"]


if __name__ == "__main__":
    clear_graph()
    _graph_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bird_dev_graph_dataset",
    )

    db_name = "california_schools"

    entity_map, edge_map = load_schema(db_name)
    _all_nodes = find_csv_files(_graph_path + "/nodes", db_name)
    _all_edges = find_csv_files(_graph_path + "/edges", db_name)
    for node in _all_nodes:
        node_type = os.path.basename(node)
        node_type = node_type.split(".")[1]
        info = entity_map[node_type]
        import_node(
            db_name,
            node_type,
            info["pk"],
            get_type_map_from_graph_schema(db_name, node_type),
        )

    for edge in _all_edges:
        spo_str = os.path.basename(edge)
        spo_str = spo_str.split(".")[1]
        edge_info = edge_map[spo_str]
        s = edge_info["s"]
        o = edge_info["o"]
        import_edge(
            db_name,
            s,
            edge_info["edge_type"],
            o,
        )
