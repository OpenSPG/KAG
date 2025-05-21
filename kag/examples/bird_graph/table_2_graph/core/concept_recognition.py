"""
直接一度关系识别
"""

import os
import json

from regex import F

from kag.examples.bird_graph.table_2_graph.m_schema.func import (
    get_m_schema,
    get_tables_m_schema_str,
    get_table_pk,
    get_table_fk_map,
)

from kag.solver.utils import init_prompt_with_fallback


from kag.common.conf import KAG_CONFIG
from kag.interface.common.llm_client import LLMClient

llm: LLMClient = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])


def get_concept_schema(bird_path: str, db_name: str):
    """
    获取边schema
    """

    prompt_op = init_prompt_with_fallback("one_degree_edge", "default")

    mschema = get_m_schema(bird_path=bird_path, db_name=db_name, with_csv_info=True)
    talbe_list = list(mschema.tables.keys())
    concept_schema_map = {}
    for table in talbe_list:
        concept_schema_map[table] = {}
        other_tables = [t for t in talbe_list if t != table]
        table_m_str = get_tables_m_schema_str(mschema, [table])
        other_m_str = get_tables_m_schema_str(
            mschema, other_tables, with_foreign_key=True
        )
        column_info_list = llm.invoke(
            variables={"table_schema": table_m_str, "other_tables_schema": other_m_str},
            prompt_op=prompt_op,
            with_json_parse=False,
            with_cache=True,
        )
        pk = get_table_pk(mschema, table)
        for column in column_info_list:
            column_name = column.pop("column")
            column_type = column.get("type", "other")
            if column_type in ["other", "primary_key"]:
                continue
            if column_name == pk:
                continue
            concept_schema_map[table][column_name] = column
        fk_map = get_table_fk_map(mschema, table)
        for column, target_columns in fk_map.items():
            concept_schema_map[table][column] = {
                "type": "foreign_key",
                "target_column": target_columns,
            }
    return concept_schema_map


def relation_naming(bird_path: str, db_name: str, concept_schema_map: dict):
    """
    关系去重，并命名
    """
    prompt_op = init_prompt_with_fallback("one_degree_edge_naming", "default")

    edge_list = []
    mschema = get_m_schema(bird_path, db_name, with_csv_info=True)
    for table, table_info in concept_schema_map.items():
        pk = get_table_pk(mschema, table)
        for column, column_info in table_info.items():
            if column_info["type"] != "foreign_key":
                continue
            for target in column_info["target_column"]:
                target_table = target.split(".")[0]
                target_column = target.split(".")[1]
                target_pk = get_table_pk(mschema, target_table)
                if target_column != target_pk:
                    continue
                foreign_key_str = f"{table}.{column} = {target_table}.{target_column}"
                schema_str = get_tables_m_schema_str(mschema, [table, target_table])
                relation_info = llm.invoke(
                    variables={
                        "table_schema": schema_str,
                        "foreign_key": foreign_key_str,
                    },
                    prompt_op=prompt_op,
                    with_json_parse=False,
                    with_cache=True,
                )
                res = str(relation_info.pop("reasonable", "false")).lower()
                if "false" == res:
                    continue
                relation_info["data_table"] = table
                edge_list.append(relation_info)
    return edge_list


def concept_naming(bird_path: str, db_name: str, concept_schema_map: dict):
    """
    为概念命名
    """
    prompt_op = init_prompt_with_fallback("two_degree_edge_naming", "default")
    edge_list = []
    mschema = get_m_schema(bird_path, db_name, with_csv_info=True)
    for table, table_info in concept_schema_map.items():
        for column, column_info in table_info.items():
            if column_info["type"] != "concept":
                continue
            target_column_l = column_info["target_column"]
            if isinstance(target_column_l, str):
                target_column_l = [target_column_l]
            for target in target_column_l:
                target_table = target.split(".")[0]
                target_column = target.split(".")[1]
                # 主键去除
                pk = get_table_pk(mschema, table)
                target_pk = get_table_pk(mschema, target_table)
                if column == pk or target_pk == target_column:
                    continue
                # 去除已有的边

                foreign_key_str = f"{table}.{column} = {target_table}.{target_column}"
                schema_str_1 = get_tables_m_schema_str(mschema, [table])
                schema_str_2 = get_tables_m_schema_str(mschema, [target_table])
                relation_info = llm.invoke(
                    variables={
                        "map_info": foreign_key_str,
                        "table_schema_1": schema_str_1,
                        "table_schema_2": schema_str_2,
                    },
                    prompt_op=prompt_op,
                    with_json_parse=False,
                    with_cache=True,
                )
                res = relation_info.pop("reasonable", "false").lower()
                if "false" == res:
                    continue
                relation_info["table1"] = table
                relation_info["table2"] = target_table
                relation_info["column1"] = column
                relation_info["column2"] = target_column
                edge_list.append(relation_info)
    return edge_list


def check_concept_edge_exist(
    one_degree_edge_list: list, table1, column1, table2, column2
):
    edge_map = {}
    for edge in one_degree_edge_list:
        s = f"{edge['subject_table']}.{edge['subject_column']}"
        o = f"{edge['object_table']}.{edge['object_column']}"
        edge_map[s] = o
        edge_map[o] = s
    check_s = f"{table1}.{column1}"
    check_o = f"{table2}.{column2}"
    if check_s in edge_map and check_o in edge_map:
        print(check_s)


if __name__ == "__main__":
    # _db_name = "california_schools"
    _db_name = "financial"
    _bird_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "bird_dev_table_dataset",
    )
    import kag.examples.bird_graph.table_2_graph.prompt

    concept_schema = get_concept_schema(bird_path=_bird_path, db_name=_db_name)
    print(json.dumps(concept_schema, ensure_ascii=False))
    one_d_edge_list = relation_naming(_bird_path, _db_name, concept_schema)
    print(json.dumps(one_d_edge_list, ensure_ascii=False))
    two_d_edge_list = concept_naming(_bird_path, _db_name, concept_schema)
    print(json.dumps(two_d_edge_list, ensure_ascii=False))
    for e in two_d_edge_list:
        check_concept_edge_exist(
            one_d_edge_list, e["table1"], e["column1"], e["table2"], e["column2"]
        )
