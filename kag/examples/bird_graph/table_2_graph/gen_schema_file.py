import json


def gen_schema_file(db_name):
    entity_map = {}
    edge_map = {}
    with open(
        f"/home/zhenzhi/code/KAG/kag/examples/bird_graph/table_2_graph/bird_dev_graph_dataset/{db_name}.schema.json",
        "r",
        encoding="utf-8",
    ) as f:
        schema_info_list = json.load(f)

    for info in schema_info_list:
        if "entity_type" in info:
            entity_map[info["entity_type"]] = info
        else:
            s = info["s"]
            p = info["edge_type"]
            o = info["o"]
            spo = (s, p, o)
            edge_map[spo] = info
    for spo, info in edge_map.items():
        s, p, o = spo
        if "edge_list" not in entity_map[s]:
            entity_map[s]["edge_list"] = {}
        entity_map[s]["edge_list"][p] = o
    return entity_map, edge_map


def property_name_fix(property_name):
    property_name = property_name.replace(" ", "")
    property_name = property_name.replace("(", "")
    property_name = property_name.replace(")", "")
    property_name = property_name.replace(",", "")
    property_name = property_name.replace("，", "")
    property_name = property_name.replace("（", "")
    property_name = property_name.replace("）", "")
    property_name = property_name.replace("/", "")
    property_name = property_name.replace("%", "")
    property_name = property_name.replace("-", "")
    return property_name


def capitalize_first_letter(s):
    # 检查字符串是否为空
    if not s:
        return s  # 如果字符串为空，直接返回

    # 将首字母大写，其余部分保持不变
    return s[0].upper() + s[1:]


def lower_first_letter(s):
    if not s:
        return s
    return s[0].lower() + s[1:]


def add_a_to_numeric_start(s):
    if s and s[0].isdigit():
        return "a" + s
    return s


if __name__ == "__main__":
    entity_map, _ = gen_schema_file(db_name="california_schools")
    entity_schema_str = "namespace BirdGraph\n\nChunk(文本块): EntityType\n    properties:\n        content(内容): Text\n            index: TextAndVector\n\n"
    for _type, entity in entity_map.items():
        _type = capitalize_first_letter(_type)
        entity_str = f"{_type}({_type}): EntityType\n    properties:\n"
        if "property_list" in entity:
            for k, v in entity["property_list"].items():
                k = property_name_fix(k)
                k = lower_first_letter(k)
                k = add_a_to_numeric_start(k)
                v = property_name_fix(v)
                entity_str += f"        {k}({v}): Text\n"
        else:
            entity_str += "        entity_name(名称): Text\n"
        if "edge_list" in entity:
            for k, v in entity["edge_list"].items():
                k = property_name_fix(k)
                k = add_a_to_numeric_start(k)
                v = capitalize_first_letter(v)
                v = property_name_fix(v)
                entity_str += f"        {k}({k}): {v}\n"
        entity_schema_str += f"{entity_str}\n"
    print(entity_schema_str)
