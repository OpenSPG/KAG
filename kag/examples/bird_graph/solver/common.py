import os
import json


def load_graph_mschema(db_name: str):
    """
    组织Graph的mschema
    """
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(
        current_file_path,
        "..",
        "table_2_graph",
        "bird_dev_graph_dataset",
        f"{db_name}.schema.json",
    )
    with open(schema_file) as f:
        graph_schema = json.load(f)
    graph_m_schema_str = "【GraphSchema】\n"
    entity_mschema_list = []
    edge_mschema_list = []
    for item in graph_schema:
        if "entity_type" in item:
            entity_mschema_list.append(get_entity_mschema_str(item, db_name))
        elif "edge_type" in item:
            edge_mschema_list.append(get_edge_mschema_str(item, db_name))
    graph_m_schema_str += "#### Entity\n"
    graph_m_schema_str += "\n".join(entity_mschema_list)
    graph_m_schema_str += "\n\n#### Edge\n[\n"
    graph_m_schema_str += "\n".join(edge_mschema_list)
    graph_m_schema_str += "\n]"
    return graph_m_schema_str


def get_entity_mschema_str(entity_info, db_name):
    desc_map = entity_info["property_list"]
    _str = f"##### {db_name}_{entity_info['entity_type']}\n["
    for attr_info in entity_info["schema"]:
        attr_name = attr_info["column_name"]
        attr_type: str = attr_info["column_type"]
        attr_example = attr_info["sample_data"][:3]
        desc = desc_map.get(attr_name, "")
        if attr_type.lower().startswith("int") or attr_type.lower().startswith("float"):
            attr_example = None
        _str += f"\n (`{attr_name}`, {attr_type}, {desc}"
        if attr_example:
            _str += f", {str(attr_example)}"
        _str += ")"
    _str += "\n]"
    return _str


def get_edge_mschema_str(edge_info, db_name):
    s = edge_info["s"]
    p = edge_info["edge_type"]
    o = edge_info["o"]
    desc = edge_info.get("desc", "")
    _str = f"  (edge_type:{p}, from:{db_name}_{s}, to:{db_name}_{o}, {desc})"
    return _str
