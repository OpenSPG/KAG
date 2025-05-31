import json
from io import StringIO
import pandas as pd


def extractor_field(entity_type, field_names):
    with open(
        "/Users/tangkun/workspace/KAG/kag/examples/bird_graph/table_2_graph/risk_sentiments_event/RiskSentimentsEventQA.Event.csv",
        "r",
        encoding="utf-8",
    ) as file:
        data = file.read()

    # 初始化结果列表
    fields = []
    property_list = {}

    # 提取字段定义部分
    start_index = data.find("(") + 1
    end_index = data.find(")", start_index)
    field_definitions = data[start_index:end_index].strip()

    # read sample data
    sample_data = extractor_field_data()

    # 分割每一行字段定义
    for line in field_definitions.split("\n"):
        line = line.strip()
        if not line:  # 跳过空行
            continue

        # 提取字段名称、字段类型和字段注释
        field_name, rest = line.split(" ", 1)
        if field_name not in field_names:
            continue

        field_name = to_camel_case(field_name)
        field_type, comment_part = rest.split(" COMMENT ", 1)
        field_comment = comment_part.strip().strip(",").strip("'")
        # 添加到结果列表
        fields.append(
            {
                "column_name": field_name,
                "column_type": field_type.strip(),
                "field_comment": field_comment,
                "sample_data": list(sample_data[field_name]),
            }
        )
        property_list[field_name] = field_comment

    schema = {
        "entity_type": entity_type,
        "pk": "id",
        "schema": fields,
        "property_list": property_list,
    }

    schemas = [schema]

    return schemas


def to_camel_case(field_name):
    parts = field_name.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def extract_unique_values(df, column):
    return df[column].dropna().unique()[:5]


def extractor_field_data():
    with open(
        "/Users/tangkun/workspace/KAG/kag/examples/bird_graph/table_2_graph/risk_sentiments_event/risk_sentiments_event.data.csv",
        "r",
        encoding="utf-8",
    ) as file:
        data = file.read()
    df = pd.read_csv(StringIO(data))
    results = {}
    for column in df.columns:
        camel_column = to_camel_case(column)
        results[camel_column] = extract_unique_values(df, column)
    return results


if __name__ == "__main__":
    field_names = [
        "event_content",
        "obj_name",
        "event_type_desc",
        "record_name",
        "gmt_occur",
    ]
    entity_type = "RiskSentimentsEventQA.Event"
    schemas = extractor_field(entity_type, field_names)

    print(json.dumps(schemas, ensure_ascii=False, indent=4))
