"""
关系表识别
"""

import os
import json

from kag.interface.common.llm_client import LLMClient
from kag.examples.bird_graph.table_2_graph.m_schema.func import (
    get_m_schema,
    get_table_fk_map,
    get_tables_m_schema_str,
    get_table_pk,
)
from kag.examples.bird_graph.table_2_graph.m_schema.m_schema import MSchema


def check_table_has_foreign_key(table_name, mschema: MSchema):
    """
    检查当前表是否被外键关联
    """
    fk_list = []
    for fk in mschema.foreign_keys:
        table1 = fk[0]
        column1 = fk[1]
        table2 = fk[3]
        column2 = fk[1]
        table_pk = get_table_pk(mschema, table_name)
        if table1 == table_name and table_pk == column1:
            fk_list.append(f"{table2}.{column2}")
        if table2 == table_name and table_pk == column2:
            fk_list.append(f"{table1}.{column1}")
    return fk_list


def get_graph_base_schema(bird_path: str, db_name: str):
    """
    获得图基础schema信息
    """
    from kag.solver.utils import init_prompt_with_fallback

    prompt_op = init_prompt_with_fallback("base_schema", "default")

    from kag.common.conf import KAG_CONFIG
    from kag.interface.common.llm_client import LLMClient

    llm: LLMClient = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])

    mschema = get_m_schema(bird_path=bird_path, db_name=db_name, with_csv_info=False)
    mschema_csv_info = get_m_schema(
        bird_path=bird_path, db_name=db_name, with_csv_info=True
    )
    talbe_list = list(mschema.tables.keys())
    entity_list = []
    edge_list = []
    for table in talbe_list:
        other_tables = [t for t in talbe_list if t != table]
        table_m_str = get_tables_m_schema_str(mschema_csv_info, [table])
        fk = check_table_has_foreign_key(table_name=table, mschema=mschema)
        if fk:
            table_m_str += f"\nThe primary key of this table[{table}] is referenced by foreign key[{fk}].\n"
        other_m_str = get_tables_m_schema_str(
            mschema, other_tables, with_foreign_key=True
        )
        table_convert_schema = llm.invoke(
            variables={"table_schema": table_m_str, "other_tables_schema": other_m_str},
            prompt_op=prompt_op,
            with_json_parse=False,
            with_cache=True,
        )
        table_convert_schema["data_table"] = table
        if "true" == table_convert_schema.pop("is_relation_table", "false").lower():
            edge_list.append(table_convert_schema)
        else:
            entity_list.append(table_convert_schema)
    return {"entity_list": entity_list, "edge_list": edge_list}, mschema


if __name__ == "__main__":
    # _db_name = "california_schools"
    _db_name = "financial"
    _bird_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "bird_dev_table_dataset",
    )

    from kag.examples.bird_graph.table_2_graph.prompt.base_schema import (
        BasehSchemaPrompt,
    )

    graph_base_schema, mschema = get_graph_base_schema(
        bird_path=_bird_path, db_name=_db_name
    )
    print(json.dumps(graph_base_schema, ensure_ascii=False))
