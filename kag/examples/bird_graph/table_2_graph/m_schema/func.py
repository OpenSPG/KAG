import os
import csv
import json
from table_2_graph.m_schema.schema_engine import SchemaEngine
from table_2_graph.m_schema.m_schema import MSchema
from sqlalchemy import create_engine


def parse_csv_to_dict(csv_file_path):
    # Initialize an empty dictionary
    field_dict = {}

    # Open the CSV file and read its contents
    with open(csv_file_path, mode="r", encoding="utf-8") as file:
        # Use the csv reader to parse the file
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            # Use 'original_column_name' as the key
            key = row["original_column_name"].strip()

            # Exclude rows where the key is empty
            if key:
                # Add the entire row to the dict with 'original_column_name' as key
                field_dict[key] = {
                    "column_name": row["column_name"],
                    "column_description": row["column_description"],
                    "data_format": row["data_format"],
                    "value_description": row["value_description"],
                }

    return field_dict


def get_csv_table_info(bird_path: str, db_name: str, table_name: str):
    """
    获取csv文件中表格的信息
    """
    csv_file = os.path.join(
        bird_path,
        "dev_databases",
        f"{db_name}",
        "database_description",
        f"{table_name}.csv",
    )
    field_dict = parse_csv_to_dict(csv_file)
    return field_dict


def get_m_schema(bird_path: str, db_name: str, with_csv_info=True):
    abs_path = os.path.join(
        bird_path, "dev_databases", f"{db_name}", f"{db_name}.sqlite"
    )
    db_engine = create_engine(f"sqlite:///{abs_path}")
    schema_engine = SchemaEngine(engine=db_engine, db_name=db_name)
    mschema: MSchema = schema_engine.mschema
    if not with_csv_info:
        return mschema
    for table_name, table_info in mschema.tables.items():
        csv_table_info = get_csv_table_info(bird_path, db_name, table_name)
        for field_name, field_info in table_info["fields"].items():
            csv_field_info = csv_table_info.get(field_name, None)
            if csv_field_info is None:
                continue
            column_name = csv_field_info["column_name"]
            if column_name.lower() == field_name.lower():
                column_name = ""
            column_desc = csv_field_info["column_description"]
            if (
                column_desc.lower() == field_name.lower()
                or column_desc.lower() == column_name.lower()
            ):
                column_desc = ""
            value_desc = csv_field_info["value_description"]
            desc = "\n".join(filter(None, [column_name, column_desc, value_desc]))
            old_comment = field_info["comment"]
            new_comment = json.dumps(desc, ensure_ascii=False)
            if not old_comment and new_comment:
                field_info["comment"] = new_comment
    return mschema


def get_m_schema_str(bird_path: str, db_name: str):
    mschema = get_m_schema(bird_path, db_name)
    mschema_str = mschema.to_mschema()
    return mschema_str


def get_tables_m_schema_str(
    mschema: MSchema, selected_tables: list[str], with_foreign_key=False
):
    m_str = mschema.to_mschema(
        selected_tables=selected_tables,
        with_prefix=False,
        with_foreign_key=with_foreign_key,
    )
    return m_str


def get_table_pk(mschema: MSchema, table_name: str):
    table_info = mschema.tables[table_name]
    for field_name, field_info in table_info["fields"].items():
        if field_info["primary_key"]:
            return field_name
    return None


def get_table_fk_map(mschema: MSchema, table_name: str):
    fk_map = {}
    fks = mschema.foreign_keys
    for fk in fks:
        table1 = fk[0]
        column1 = fk[1]
        table2 = fk[3]
        column2 = fk[4]
        if table1 != table_name:
            continue
        if column1 not in fk_map:
            fk_map[column1] = []
        fk_map[column1].append(f"{table2}.{column2}")
    return fk_map


def get_column_list_from_mschema(table_name: str, mschema: MSchema):
    column_list = mschema.tables[table_name]["fields"]
    return [
        {"name": c, "type": info["type"], "primary_key": info["primary_key"]}
        for c, info in column_list.items()
    ]


if __name__ == "__main__":
    _db_list = [
        # "california_schools",
        # "card_games",
        "financial",
    ]
    for _db_name in _db_list:
        # 1.connect to the database engine
        _db_path = (
            f"/Users/youdonghai/code/nl2ql/NL2QL/table_2_graph/bird_dev_table_dataset/"
        )
        _mschema_str = get_m_schema_str(_db_path, db_name=_db_name)
        print(_mschema_str)
