#coding=utf8
import random
import re
import string


def generate_random_string(bit=8):
    possible_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(possible_characters) for _ in range(bit))

def generate_biz_id_with_type(biz_id, type_name):
    return f"{biz_id}_{type_name}"

def get_p_clean(p):
    if re.search(".*[\\u4e00-\\u9fa5]+.*", p):
        p = re.sub('[ \t:：（）“”‘’\'"\[\]\(\)]+?', '', p)
    else:
        p = None
    return p

def get_recall_node_label(label_set):
    for l in label_set:
        if l != "Entity":
            return l
def node_2_doc(node:dict):
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