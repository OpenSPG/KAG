# coding=utf8
import random
import re
import string


def generate_random_string(bit=8):
    possible_characters = string.ascii_letters + string.digits
    random_str = "".join(random.choice(possible_characters) for _ in range(bit))
    return "gen" + random_str


def generate_biz_id_with_type(biz_id, type_name):
    return f"{biz_id}_{type_name}"


def get_p_clean(p):
    if re.search(".*[\\u4e00-\\u9fa5]+.*", p):
        p = re.sub("[ \t:：（）“”‘’'\"\[\]\(\)]+?", "", p)
    else:
        p = None
    return p


def get_recall_node_label(label_set):
    for l in label_set:
        if l != "Entity":
            return l


def node_2_doc(node: dict):
    prop_set = []
    for key in node.keys():
        if key in ["id"]:
            continue
        value = node[key]
        if isinstance(value, list):
            value = "\n".join(value)
        else:
            value = str(value)
        if key == "name":
            prop = f"节点名称:{value}"
        elif key == "description":
            prop = f"描述:{value}"
        else:
            prop = f"{key}:{value}"
        prop_set.append(prop)
    return "\n".join(prop_set)


def extract_content_target(input_string):
    """
    Extract the content and target parts from the input string.

    Args:
        input_string (str): A string containing content and target.

    Returns:
        dict: A dictionary containing 'content' and 'target'. If not found, the corresponding value is None.
    """
    # Define regex patterns
    # Content may contain newlines and special characters, so use non-greedy mode
    content_pattern = r"content=\[(.*?)\]"
    target_pattern = (
        r"target=([^,\]]+)"  # Assume target does not contain commas or closing brackets
    )

    # Search for content
    content_match = re.search(content_pattern, input_string, re.DOTALL)
    if content_match:
        content = content_match.group(1).strip()
    else:
        content = None

    # Search for target
    target_match = re.search(target_pattern, input_string)
    if target_match:
        target = (
            target_match.group(1).strip().rstrip("'")
        )  # Remove trailing single quote if present
    else:
        target = None
    return content, target
