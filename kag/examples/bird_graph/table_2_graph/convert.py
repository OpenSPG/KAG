import re
import kag.examples.bird_graph.table_2_graph.prompt


import os
import json
import sqlite3

from kag.examples.bird_graph.table_2_graph.m_schema.func import (
    get_column_list_from_mschema,
    get_table_pk,
)
from kag.examples.bird_graph.table_2_graph.core.entity_relation_recongnition import (
    get_graph_base_schema,
)
from kag.examples.bird_graph.table_2_graph.core.concept_recognition import (
    get_concept_schema,
    relation_naming,
    concept_naming,
)
from kag.examples.bird_graph.table_2_graph.core.convert_2_graph import (
    convert_node,
    convert_table_edge,
    convert_fk_edge,
    convert_concept_edge,
)


def standardize_name(name: str):
    """
    标准化名称，移除所有下划线和空格
    :param name: 输入的名称字符串
    :return: 标准化后的名称字符串
    """
    # 使用 str.replace 并先移除下划线，再移除空格
    standardized_name = name.replace("_", "").replace(" ", "")
    return standardized_name


def remove_duplicate_edges(edge_list):
    new_list = []
    edge_key_set = set()
    for edge in edge_list:
        edge_type = edge["type"]
        if "fk_edge" == edge_type:
            s_t = edge["subject_table"]
            o_t = edge["object_table"]
            s_c = edge["subject_column"]
            o_c = edge["object_column"]
            key1 = f"fk_{s_t}.{s_c}={o_t}.{o_c}"
            key2 = f"fk_{o_t}.{o_c}={s_t}.{s_c}"
            if key1 in edge_key_set or key2 in edge_key_set:
                continue
            edge_key_set.add(key1)
            edge_key_set.add(key2)
            new_list.append(edge)
        elif "concept_edge" == edge_type:
            s_t = edge["subject_table"]
            s_c = edge["subject_column"]
            o_t_l = edge["object_table"]
            o_t_l = sorted(o_t_l)
            key = f"c_{s_t}.{s_c}.{o_t_l}"
            if key in edge_key_set:
                continue
            edge_key_set.add(key)
            new_list.append(edge)
        else:
            new_list.append(edge)
    return new_list


def merge_convert_info(
    base_schema, one_degree_edge_list, two_degree_edge_list, mschema
):
    """
    合并转换信息
    """
    entity_name_set = set()
    entity_list = base_schema["entity_list"]
    for entity in entity_list:
        table_name = entity["data_table"]
        entity_name_set.add(table_name)
        pk = get_table_pk(mschema, table_name)
        entity["pk"] = pk

    edge_list = base_schema["edge_list"]
    for edge in edge_list:
        edge["type"] = "table_edge"
    for one_degree_edge in one_degree_edge_list:
        one_degree_edge["type"] = "fk_edge"
        one_degree_edge["edge_type"] = standardize_name(one_degree_edge["edge_type"])
        subject_table = one_degree_edge["subject_table"]
        object_table = one_degree_edge["object_table"]
        if subject_table not in entity_name_set and object_table not in entity_name_set:
            continue
        edge_list.append(one_degree_edge)
    for two_degree_edge in two_degree_edge_list:
        two_degree_edge["edge_type_1"] = standardize_name(
            two_degree_edge["edge_type_1"]
        )
        two_degree_edge["edge_type_2"] = standardize_name(
            two_degree_edge["edge_type_2"]
        )
        two_degree_edge["entity_type"] = standardize_name(
            two_degree_edge["entity_type"]
        )
        table1 = two_degree_edge["table1"]
        table2 = two_degree_edge["table2"]
        column1 = two_degree_edge["column1"]
        column2 = two_degree_edge["column2"]
        edge_type1 = two_degree_edge["edge_type_1"]
        edge_type2 = two_degree_edge["edge_type_2"]
        entity_type = two_degree_edge["entity_type"]
        edge1 = {
            "type": "concept_edge",
            "edge_type": edge_type1,
            "subject_table": table1,
            "object_table": [table1, column1, table2, column2],
            "subject_column": column1,
            "object_column": "id",
            "data_table": table1,
            "entity_type": entity_type,
        }
        edge2 = {
            "type": "concept_edge",
            "edge_type": edge_type2,
            "subject_table": table2,
            "object_table": [table1, column1, table2, column2],
            "subject_column": column2,
            "object_column": "id",
            "data_table": table2,
            "entity_type": entity_type,
        }
        if table1 in entity_name_set:
            edge_list.append(edge1)
        if table2 in entity_name_set:
            edge_list.append(edge2)
    base_schema["edge_list"] = remove_duplicate_edges(base_schema["edge_list"])
    return base_schema


def convert_one_db(bird_path, db_name):
    base_schema, mschema = get_graph_base_schema(bird_path=bird_path, db_name=db_name)
    print(json.dumps(base_schema, ensure_ascii=False))
    concept_schema = get_concept_schema(bird_path=bird_path, db_name=db_name)
    one_degree_edge_list = relation_naming(bird_path, db_name, concept_schema)
    print(json.dumps(one_degree_edge_list, ensure_ascii=False))
    two_degree_edge_list = concept_naming(bird_path, db_name, concept_schema)
    print(json.dumps(two_degree_edge_list, ensure_ascii=False))
    convert_info = merge_convert_info(
        base_schema, one_degree_edge_list, two_degree_edge_list, mschema
    )
    print(json.dumps(convert_info, ensure_ascii=False))

    bird_graph_data_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bird_dev_graph_dataset",
    )
    node_path = os.path.join(bird_graph_data_path, "nodes")
    edge_path = os.path.join(bird_graph_data_path, "edges")
    os.makedirs(node_path, exist_ok=True)
    os.makedirs(edge_path, exist_ok=True)

    from_db_sqlite = os.path.join(
        bird_path, "dev_databases", db_name, f"{db_name}.sqlite"
    )
    conn = sqlite3.connect(from_db_sqlite, check_same_thread=False)
    for entity in convert_info["entity_list"]:
        table_name = entity["data_table"]
        convert_node(
            db_name,
            table_name,
            get_column_list_from_mschema(table_name, mschema),
            conn,
            node_path,
        )
    for edge in convert_info["edge_list"]:
        convert_type = edge["type"]
        table_name = edge["data_table"]
        if "table_edge" == convert_type:
            s = edge["subject_table"]
            o = edge["object_table"]
            p = edge["edge_type"]
            s_column = edge["subject_column"]
            o_column = edge["object_column"]
            convert_table_edge(
                db_name,
                conn,
                edge_path,
                table_name,
                mschema,
                s,
                o,
                p,
                s_column,
                o_column,
            )
        elif "fk_edge" == convert_type:
            s = f"{edge['subject_table']}.{edge['subject_column']}"
            o = f"{edge['object_table']}.{edge['object_column']}"
            p = edge["edge_type"]
            convert_fk_edge(
                db_name,
                conn,
                edge_path,
                table_name,
                mschema,
                s,
                o,
                p,
            )
        else:
            s = f"{edge['subject_table']}.{edge['subject_column']}"
            o = edge["object_table"]
            p = edge["edge_type"]
            o_type = edge["entity_type"]
            convert_concept_edge(
                db_name,
                conn,
                edge_path,
                node_path,
                table_name,
                mschema,
                s,
                o,
                p,
                o_type,
            )
        schema_file = os.path.join(bird_graph_data_path, f"{db_name}.schema.json")
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(convert_info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    _bird_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bird_dev_table_dataset",
    )
    _db_list = [
        "california_schools",
        # "formula_1",
        # "debit_card_specializing",
        # "financial",
        # "card_games",
        # "european_football_2",
        # "thrombosis_prediction",
        # "toxicology",
        # "student_club",
        # "superhero",
        # "codebase_community",
    ]
    for _db_name in _db_list:
        convert_one_db(_bird_path, _db_name)
