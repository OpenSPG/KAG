import json
import os
import sqlite3

import polars as pl

from kag.examples.bird_graph.table_2_graph.m_schema.m_schema import MSchema
from kag.examples.bird_graph.table_2_graph.m_schema.func import (
    get_column_list_from_mschema,
    get_table_pk,
)

WRITE_FLAG = True


def get_datetime_columns(table_column_list):
    rst_map = {}
    for column in table_column_list:
        name = column["name"]
        column_type = column["type"]
        if column_type == "DATETIME":
            rst_map[name] = pl.Datetime
        elif column_type == "DATE":
            rst_map[name] = pl.Date
    return rst_map


def get_df_schema(df: pl.DataFrame, table_column_list):
    result = []
    datetime_col_map = get_datetime_columns(table_column_list)
    for col in df.columns:
        column_data = df[col]
        column_type = column_data.dtype
        # 抽样 5 个不同的数据，过滤掉 null
        sampled_data = column_data.drop_nulls().unique().limit(5).to_list()
        if col in datetime_col_map:
            column_type = datetime_col_map[col]
        result.append(
            {
                "column_name": col,
                "column_type": str(column_type),
                "sample_data": sampled_data,
            }
        )
    return result


def convert_node(
    db_id, table_name: str, columns: list, conn: sqlite3.Connection, node_path: str
):
    """
    转换表节点
    """
    df, pk = get_df_from_sqlite(conn, table_name, columns)
    table_name = table_name.replace(" ", "")
    node_type = f"{db_id}.{table_name}"
    csv_file = os.path.join(node_path, f"{node_type}.csv")
    if WRITE_FLAG:
        df.write_csv(csv_file, include_header=True)
    return {"entity_type": table_name, "pk": pk, "schema": get_df_schema(df, columns)}


def get_df_from_sqlite(conn: sqlite3.Connection, table_name: str, table_column_list):
    """
    sqlite表转换为df
    """

    def get_primary_key(table_column_list):
        for column in table_column_list:
            if column["primary_key"]:
                return column["name"]
        return None

    def get_table_schema(table_column_list):
        type_map = {
            "INTEGER": pl.Int64,
            "TEXT": pl.String,
            "DATETIME": pl.String,
            "DATE": pl.String,
            "REAL": pl.Float64,
        }
        schema = {}
        for column in table_column_list:
            name = column["name"]
            column_type = column["type"]
            schema[name] = type_map[column_type]
        return schema

    df = pl.read_database(
        f"SELECT * FROM `{table_name}`",
        conn,
        schema_overrides=get_table_schema(table_column_list),
    )
    pk = get_primary_key(table_column_list)
    if pk is None or (pk == "id" and pk not in df.columns):
        df = df.with_columns(pl.Series("id", range(len(df))))
        pk = "id"
    return df, pk


def convert_table_edge(
    db_name,
    conn: sqlite3.Connection,
    edge_path: str,
    table_name: str,
    mschema: MSchema,
    s_table: str,
    o_table: str,
    p: str,
    s_column: str,
    o_column: str,
):
    table_columns = get_column_list_from_mschema(table_name, mschema)
    df, pk = get_df_from_sqlite(conn, table_name, table_columns)
    df = df.rename(mapping={s_column: "s", o_column: "o"}).with_columns(p=pl.lit(p))
    edge_file = f"{db_name}.{s_table}_{p}_{o_table}"
    csv_file = os.path.join(edge_path, f"{edge_file}.csv")
    if WRITE_FLAG:
        df.write_csv(csv_file, include_header=True)
    return {"edge_type": p, "s": s_table, "o": o_table}


def convert_fk_edge(
    db_name,
    conn: sqlite3.Connection,
    edge_path: str,
    table_name: str,
    mschema: MSchema,
    s_column: str,
    o_column: str,
    p: str,
):
    s_table = s_column.split(".")[0]
    s_column = s_column.split(".")[1]
    o_table = o_column.split(".")[0]
    o_column = o_column.split(".")[1]
    if table_name == o_table:
        # 是IN边
        s_table, o_table = o_table, s_table
        s_column, o_column = o_column, s_column
    if s_column == get_table_pk(mschema, s_table) and o_column == get_table_pk(
        mschema, o_table
    ):
        df1, pk1 = get_df_from_sqlite(
            conn, s_table, get_column_list_from_mschema(s_table, mschema)
        )
        df2, pk2 = get_df_from_sqlite(
            conn, o_table, get_column_list_from_mschema(o_table, mschema)
        )
        df1 = df1.select(id=pl.col(pk1))
        df2 = df2.select(id=pl.col(pk2))
        df = df1.filter(df1["id"].is_in(df2["id"])).unique()
        df = df.select(s=pl.col("id"), p=pl.lit(p), o=pl.col("id"))
    else:
        table_columns = get_column_list_from_mschema(table_name, mschema)
        df, pk = get_df_from_sqlite(conn, table_name, table_columns)
        df = df.select([pk, pl.lit(p).alias("p"), o_column]).rename(
            mapping={pl: "s", o_column: "o"}
        )
    edge_file = f"{db_name}.{table_name}_{p}_{o_table}"
    csv_file = os.path.join(edge_path, f"{edge_file}.csv")
    if WRITE_FLAG:
        df.write_csv(csv_file, include_header=True)
    return {"edge_type": p, "s": table_name, "o": o_table}
    # print(csv_file)
    # print(df.head(3))


def convert_concept_edge(
    db_name,
    conn: sqlite3.Connection,
    edge_path: str,
    node_path: str,
    table_name: str,
    mschema: MSchema,
    s_column: str,
    o_entity_info_list: list[str],
    p: str,
    o_type: str,
):
    table1 = o_entity_info_list[0]
    column1 = o_entity_info_list[1]
    table2 = o_entity_info_list[2]
    column2 = o_entity_info_list[3]
    df1, pk = get_df_from_sqlite(
        conn, table1, get_column_list_from_mschema(table1, mschema)
    )
    df2, pk = get_df_from_sqlite(
        conn, table2, get_column_list_from_mschema(table2, mschema)
    )
    try:
        df1 = df1.select(id=pl.col(column1))
        df2 = df2.select(id=pl.col(column2))
    except pl.exceptions.ColumnNotFoundError:
        # 列不存在
        return
    intersection_df = df1.filter(df1["id"].is_in(df2["id"])).unique()
    if len(intersection_df) <= 0:
        # 无交集，不存在二度关系
        return
    try:
        df = pl.concat([df1, df2]).unique()
    except pl.exceptions.SchemaError:
        # 类型不同，直接跳过
        return
    len_df = len(df)
    if len_df <= 3:
        # 数量太少，无意义
        return
    len_df1 = len(df1)
    len_df2 = len(df2)
    if len_df1 / len_df > 1000 or len_df2 / len_df > 1000:
        # 热点太大，不要这个边
        return
    entity_file_name = f"{db_name}.{o_type}"
    csv_file = os.path.join(node_path, f"{entity_file_name}.csv")
    if WRITE_FLAG:
        df.write_csv(csv_file, include_header=True)

    s_table = s_column.split(".")[0]
    s_column = s_column.split(".")[1]
    edge_file_name = f"{db_name}.{s_table}_{p}_{o_type}"
    edge_csv_file = os.path.join(edge_path, f"{edge_file_name}.csv")
    df, pk = get_df_from_sqlite(
        conn, table_name, get_column_list_from_mschema(table_name, mschema)
    )
    df = df.select(s=pl.col(pk), p=pl.lit(p), o=pl.col(s_column))
    if WRITE_FLAG:
        df.write_csv(edge_csv_file, include_header=True)
    return [
        {"entity_type": o_type, "pk": "id"},
        {"edge_type": p, "s": s_table, "o": o_type},
    ]


def convert_edge(
    db_id, spo_info, db_schema_info: dict, conn: sqlite3.Connection, edge_path: str
):
    """
    转换边
    edge_chema exampe =
    """
    s = spo_info["s"]
    p = spo_info["p"].replace(" ", "")
    o = spo_info["o"]
    source_table = s.split(".")[0]
    source_column = s.split(".")[1]
    target_table = o.split(".")[0]
    target_column = o.split(".")[1]

    edge_file_name = f"{db_id}.{source_table}_{p}_{target_table}"
    if edge_file_name == "codebase_community.users_voted_on_votes":
        print("x")

    # 通过value join后获得边数据
    source_df, source_pk = get_df_from_sqlite(
        conn, source_table, db_schema_info[source_table]
    )
    target_df, target_pk = get_df_from_sqlite(
        conn, target_table, db_schema_info[target_table]
    )

    # 记录转换规则
    convert_edge_rule = {
        "from_node": source_table,
        "to_node": target_table,
        "where": f"{source_table}.{source_column} = {target_table}.{target_column}",
        "name": p,
    }
    convert_rule = os.path.join(edge_path, f"{edge_file_name}.rule.json")
    with open(file=convert_rule, mode="w", encoding="utf-8") as f:
        json.dump(convert_edge_rule, f, indent=2)

    if source_column == source_pk and target_column == target_pk:
        # 主键之间的关联
        ids_from_df1 = source_df.select(id=source_column)
        ids_from_df2 = target_df.select(id=target_column)
        combined_ids = pl.concat([ids_from_df1, ids_from_df2], rechunk=True)
        df = combined_ids.with_columns(
            [pl.col("id").alias("s"), pl.col("id").alias("o")]
        )
        edge_column_map = {"s": "s", "o": "o"}
        edge_df = df.select(edge_column_map.keys()).rename(edge_column_map)
    elif source_column == source_pk:
        # source是主键
        edge_column_map = {target_column: "s", target_pk: "o"}
        edge_df = target_df.select(edge_column_map.keys()).rename(edge_column_map)
    elif target_column == target_pk:
        # target是主键
        edge_column_map = {source_column: "s", source_pk: "o"}
        edge_df = source_df.select(edge_column_map.keys()).rename(edge_column_map)
    else:
        # 值关联
        # 如果不是通过主键关联，在太大的表上join意义不大，因此df在数据量在十万以上，跳过这种join
        if len(source_df) > 100 * 10000 or len(target_df) > 100 * 10000:
            print(
                f"table to big, source={source_table},len={len(source_df)}, target={target_table},len={len(target_df)}"
            )
            return
        if source_pk == target_pk:
            rename_target_pk = "__target_pk__"
            rename_pk = {target_pk: rename_target_pk}
            target_df = target_df.rename(rename_pk)
            target_pk = rename_target_pk

        try:
            # 检查 source_column 和 target_column 的类型是否一致
            source_type = source_df.schema[source_column]
            target_type = target_df.schema[target_column]

            if source_type != target_type:
                # 类型不匹配，不join
                print(
                    f"skip join, column data type not match, {source_column}={source_type}, {target_column}={target_type}"
                )
                return

            edge_df = source_df.join(
                target_df,
                left_on=source_column,
                right_on=target_column,
                how="inner",
                suffix="_source",
            ).select([source_pk, target_pk])
        except Exception as e:
            print(f"Error during join: {e}")
            return

        edge_column_map = {}
        edge_column_map[source_pk] = "s"
        edge_column_map[target_pk] = "o"
        edge_df = edge_df.select(edge_column_map.keys()).rename(edge_column_map)

    edge_df = edge_df.with_columns(p=pl.lit(p))

    # 按照spo重新把列排序
    desired_order = ["s", "p", "o"]
    remaining_columns = [col for col in edge_df.columns if col not in desired_order]
    new_order = desired_order + remaining_columns
    edge_df = edge_df.select(new_order)

    # 去重
    edge_df = edge_df.unique(subset=["s", "p", "o"])

    # 去重s或者o为Null的数据
    edge_df = edge_df.filter(pl.col("s").is_not_null() & pl.col("o").is_not_null())

    # 检查DataFrame长度
    if len(edge_df) > 100 * 10000:
        print(f"edge size too long, {edge_file_name}, {len(edge_df)}")
        return
    if len(edge_df) <= 0:
        return

    csv_file = os.path.join(edge_path, f"{edge_file_name}.csv")
    edge_df.write_csv(csv_file, include_header=True)


def write_db_schema(db_id, db_schema, path):
    """
    写入db_schema信息
    """
    file_name = f"{db_id}.schema.json"
    json_file = os.path.join(path, file_name)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(db_schema, fp=f, ensure_ascii=False, indent=2)
