#coding=utf8
import random
import re
import json
import string
from collections import defaultdict
import os

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


def extract_location(s):
    # 修改正则表达式以支持各类省份/自治区/特别行政区等
    # 支持的格式包括直辖市、普通省份、自治区等的市和县/区的命名
    # (\w+(省|自治区|特别行政区))? 可选的省份/自治区/特别行政区
    # (-\w+(市|州))? 可选的市或州
    # (-\w+(区|县))? 可选的区或县
    pattern = r'(\w+(省|市|自治区|特别行政区))?(-\w+(市|州))?(-\w+(区|县|市|新区|自治县|旗|旗县自治旗))?'

    # 搜索字符串以找到匹配项
    matches = re.findall(pattern, s)

    # 如果找到匹配项，返回所有匹配的地理位置信息
    if matches:
        # 对于每个匹配项，提取必要的信息并合成地理位置字符串
        locations = [''.join(filter(None, match[::2])) for match in matches]  # 使用步进跳过匹配的省/自治区等后缀
        ret = []
        for l in locations:
            if l != '':
                ret.append(l)
        if len(ret) == 0:
            return None, None, None, None
        ret_full = ret[0]
        out = ret_full.split("-")
        municipality_map = ['上海市', '北京市', '天津市', '重庆市']
        prov = out[0]
        if prov in municipality_map:
            return ret_full, prov, prov, out[1] if len(out) == 2 else None
        if len(out) == 1:
            return ret_full, out[0], None, None
        if len(out) == 2:
            return ret_full, out[0], out[1], None
        if len(out) == 3:
            return ret_full, out[0], out[1], out[2]
    else:
        return None, None, None, None

