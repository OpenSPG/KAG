
def fix_schem(schema_info, db_name):
    for schema in schema_info:
        if "entity_type" not in schema:
            continue
        schema["entity_type"] = f"{db_name}_{schema['entity_type']}"
    return schema_info
