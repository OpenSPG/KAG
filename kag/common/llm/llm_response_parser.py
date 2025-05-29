import json
from typing import Any


def parse_json(content: str) -> Any:
    content = content.replace("\n", " ")

    try:
        start_idx = content.rfind("{")
        end_idx = content.rfind("}")
        obj = json.loads(content[start_idx : end_idx + 1])

    except:
        start_idx = content.rfind(': "')
        end_idx = content.rfind('"}')
        if start_idx >= 0 and end_idx >= 0:
            content = (
                content[:start_idx]
                + ': "'
                + content[start_idx + len(': "') : end_idx].replace('"', "")
                + '"}'
            )

        start_idx = content.rfind("{")
        end_idx = content.rfind("}")
        obj = json.loads(content[start_idx : end_idx + 1], strict=False)

    return obj
