import json
import re


def get_json_from_response(response):
    """
    解析LLM返回的表schema结果
    """
    pattern = r"```json\s*(.*?)\s*```"
    matches = re.findall(pattern, response, re.DOTALL)
    valid_jsons = []
    for match in matches:
        try:
            parsed_json = json.loads(match.strip())
            valid_jsons.append(parsed_json)
        except json.JSONDecodeError:
            print("Warning: Found invalid JSON content.")
            continue
    if len(valid_jsons) == 0:
        return None
    graph_schema = valid_jsons[-1]
    return graph_schema
