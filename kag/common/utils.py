# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
# flake8: noqa
import datetime
import random
import re
import string
import sys
import json
import hashlib
import os
import tempfile
import time
import uuid
import subprocess
import shlex

import requests
import importlib
import numpy as np
from typing import Tuple, TypeVar, Optional
from pathlib import Path

from shutil import copystat, copy2
from typing import Any, Union
from jinja2 import Environment, FileSystemLoader, Template
from stat import S_IWUSR as OWNER_WRITE_PERMISSION
from tenacity import retry, stop_after_attempt
from aiolimiter import AsyncLimiter

reset = "\033[0m"
bold = "\033[1m"
underline = "\033[4m"
red = "\033[31m"
green = "\033[32m"
yellow = "\033[33m"
blue = "\033[34m"
magenta = "\033[35m"
cyan = "\033[36m"
white = "\033[37m"


def run_cmd(cmd, catch_stdout=True, catch_stderr=True, shell=False):
    args = shlex.split(cmd)
    if catch_stdout:
        stdout = subprocess.PIPE
    else:
        stdout = None
    if catch_stderr:
        stderr = subprocess.PIPE
    else:
        stderr = None
    result = subprocess.run(args, stdout=stdout, stderr=stderr, shell=shell)
    return result


def append_python_path(path: str) -> bool:
    """
    Append the given path to `sys.path`.
    """
    path = Path(path).resolve()
    path = str(path)
    if path not in sys.path:
        sys.path.append(path)
        return True
    return False


def render_template(
    root_dir: Union[str, os.PathLike], file: Union[str, os.PathLike], **kwargs: Any
) -> None:
    env = Environment(loader=FileSystemLoader(root_dir))
    template = env.get_template(str(file))
    content = template.render(kwargs)

    path_obj = Path(root_dir) / file
    render_path = path_obj.with_suffix("") if path_obj.suffix == ".tmpl" else path_obj

    if path_obj.suffix == ".tmpl":
        path_obj.rename(render_path)
    render_path.write_text(content, "utf8")


def copytree(src: Path, dst: Path, **kwargs):
    names = [x.name for x in src.iterdir()]

    if not dst.exists():
        dst.mkdir(parents=True)

    for name in names:
        _name = Template(name).render(**kwargs)
        src_name = src / name
        dst_name = dst / _name
        if src_name.is_dir():
            copytree(src_name, dst_name, **kwargs)
        else:
            copyfile(src_name, dst_name, **kwargs)

    copystat(src, dst)
    _make_writable(dst)


def copyfile(src: Path, dst: Path, **kwargs):
    if dst.exists():
        return
    dst = Path(Template(str(dst)).render(**kwargs))
    copy2(src, dst)
    _make_writable(dst)
    if dst.suffix != ".tmpl":
        return
    render_template("/", dst, **kwargs)


def remove_files_except(path, file, new_file):
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path) and filename != file:
            os.remove(file_path)
    os.rename(path / file, path / new_file)


def _make_writable(path):
    current_permissions = os.stat(path).st_mode
    os.chmod(path, current_permissions | OWNER_WRITE_PERMISSION)


def escape_single_quotes(s: str):
    return s.replace("'", "\\'")


def load_json(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        substr = content[: e.colno - 1]
        return json.loads(substr)


def flatten_2d_list(nested_list):
    return [item for sublist in nested_list for item in sublist]


def split_module_class_name(name: str, text: str) -> Tuple[str, str]:
    """
    Split `name` as module name and class name pair.

    :param name: fully qualified class name, e.g. ``foo.bar.MyClass``
    :type name: str
    :param text: describe the kind of the class, used in the exception message
    :type text: str
    :rtype: Tuple[str, str]
    :raises RuntimeError: if `name` is not a fully qualified class name
    """
    i = name.rfind(".")
    if i == -1:
        message = "invalid %s class name: %s" % (text, name)
        raise RuntimeError(message)
    module_name = name[:i]
    class_name = name[i + 1 :]
    return module_name, class_name


def dynamic_import_class(name: str, text: str):
    """
    Import the class specified by `name` dyanmically.

    :param name: fully qualified class name, e.g. ``foo.bar.MyClass``
    :type name: str
    :param text: describe the kind of the class, use in the exception message
    :type text: str
    :raises RuntimeError: if `name` is not a fully qualified class name, or
                          the class is not in the module specified by `name`
    :raises ModuleNotFoundError: the module specified by `name` is not found
    """
    module_name, class_name = split_module_class_name(name, text)
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name, None)
    if class_ is None:
        message = "class %r not found in module %r" % (class_name, module_name)
        raise RuntimeError(message)
    if not isinstance(class_, type):
        message = "%r is not a class" % (name,)
        raise RuntimeError(message)
    return class_


def processing_phrases(phrase):
    phrase = str(phrase)
    return re.sub("[^A-Za-z0-9\u4e00-\u9fa5 ]", " ", phrase.lower()).strip()


def to_camel_case(phrase):
    s = processing_phrases(phrase).replace(" ", "_")
    return "".join(
        word.capitalize() if i != 0 else word for i, word in enumerate(s.split("_"))
    )


def to_snake_case(name):
    words = re.findall("[A-Za-z][a-z0-9]*", name)
    result = "_".join(words).lower()
    return result


def get_vector_field_name(property_key: str):
    name = f"{property_key}_vector"
    name = to_snake_case(name)
    return "_" + name


def get_sparse_vector_field_name(property_key: str):
    name = f"{property_key}_sparse"
    name = to_snake_case(name)
    return "_" + name


def split_list_into_n_parts(lst, n):
    length = len(lst)
    part_size = length // n
    seg = [x * part_size for x in range(n)]
    seg.append(min(length, part_size * n))

    remainder = length % n

    result = []

    # 分割列表
    start = 0
    for i in range(n):
        # 计算当前份的元素数量
        if i < remainder:
            end = start + part_size + 1
        else:
            end = start + part_size

        # 添加当前份到结果列表
        result.append(lst[start:end])

        # 更新起始位置
        start = end

    return result


def generate_hash_id(value):
    """
    Generates a hash ID and an abstracted version of the input value.

    If the input value is a dictionary, it sorts the dictionary items and abstracts the dictionary.
    If the input value is not a dictionary, it abstracts the value directly.

    Args:
        value: The input value to be hashed and abstracted.

    Returns:
        str: A hash ID generated from the input value.
    """
    if isinstance(value, dict):
        sorted_items = sorted(value.items())
        key = str(sorted_items)
    else:
        key = str(value)  # Ensure key is a string regardless of input type

    # Encode to bytes for hashing
    key = key.encode("utf-8")

    hasher = hashlib.sha256()
    hasher.update(key)

    return hasher.hexdigest()


@retry(stop=stop_after_attempt(3), reraise=True)
def download_from_http(url: str, dest: str = None) -> str:
    """Downloads a file from an HTTP URL and saves it to a temporary directory.

    This function uses the requests library to download a file from the specified
    HTTP URL and saves it to the system's temporary directory. After the download
    is complete, it returns the local path of the downloaded file.

    Args:
        url (str): The HTTP URL of the file to be downloaded.

    Returns:
        str: The local path of the downloaded file.

    """

    # Send an HTTP GET request to download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Check if the request was successful

    if dest is None:
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, os.path.basename(url))
        dest = temp_file_path

    with open(dest, "wb") as temp_file:
        # Write the downloaded content to the temporary file
        for chunk in response.iter_content(chunk_size=1024**2):
            temp_file.write(chunk)

    # Return the path of the temporary file
    return temp_file.name


class RateLimiterManger:
    def __init__(self):
        self.limiter_map = {}

    def get_rate_limiter(
        self, name: str, max_rate: float = 1000, time_period: float = 1
    ):
        if name not in self.limiter_map:
            limiter = AsyncLimiter(max_rate, time_period)
            self.limiter_map[name] = limiter
        return self.limiter_map[name]


def get_now(language="zh"):
    if language == "zh":
        days_of_week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        date_format = "%Y年%m月%d日"
    elif language == "en":
        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        date_format = "%Y-%m-%d"
    else:
        raise ValueError(
            "Unsupported language. Please use 'zh' for Chinese or 'en' for English."
        )

    today = datetime.datetime.now()
    return today.strftime(date_format) + " (" + days_of_week[today.weekday()] + ")"


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
    return "Entity"


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


def generate_unique_message_key(message):
    unique_id = uuid.uuid5(uuid.NAMESPACE_URL, str(message))
    timestamp = int(time.time() * 1000)  # 获取当前时间戳（毫秒级）
    # unique_id = uuid.uuid4().hex  # 生成一个UUID并转换为十六进制字符串
    async_message_key = f"KAG_{timestamp}_{unique_id}"
    return async_message_key


def rrf_score(length, r: int = 1):
    return np.array([1 / (r + i) for i in range(length)])


T = TypeVar("T")


def resolve_instance(
    instance: Optional[Union[T, dict]],
    default_config: dict,
    from_config_func,
    expected_type=None,
) -> T:
    if isinstance(instance, dict):
        return from_config_func(instance)
    elif instance is None:
        return from_config_func(default_config)
    elif expected_type and not isinstance(instance, expected_type):
        raise TypeError(f"Expected {expected_type}, got {type(instance)}")
    else:
        return instance


def extract_tag_content(text):
    pattern = r"<(\w+)\b[^>]*>(.*?)</\1>|<(\w+)\b[^>]*>([^<]*)|([^<]+)"
    results = []
    for match in re.finditer(pattern, text, re.DOTALL):
        tag1, content1, tag2, content2, raw_text = match.groups()
        if tag1:
            results.append((tag1, content1))  # 保留原始内容（含空格）
        elif tag2:
            results.append((tag2, content2))  # 保留原始内容（含空格）
        elif raw_text:
            results.append(("", raw_text))  # 保留原始空格
    return results


def extract_specific_tag_content(text, tag):
    # 构建正则表达式：匹配指定标签内的内容（支持嵌套相同标签）
    pattern = rf"<{tag}\b[^>]*>(.*?)</{tag}>"
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [content.strip() for content in matches]


def extract_box_answer(text):
    pattern = r"\\boxed\{([^}]*)\}"
    extracted_answers = re.findall(pattern, text)
    if len(extracted_answers) == 0:
        return ""
    else:
        return extracted_answers[0]


def remove_boxed(text):
    # 匹配 \boxed{内容} 并提取内容部分
    pattern = r"\\boxed\{([^}]*)\}"
    # 使用正则替换为仅保留大括号中的内容
    result = re.sub(pattern, r"\1", text)
    return result


def search_plan_extraction(text):
    text = text.replace("\n", "")
    pattern = r"(?i)<search.*?>.*?</search>"
    matches = re.findall(pattern, text)

    # 提取内容部分
    extracted_plans = []
    for match in matches:
        # 使用非贪婪匹配提取内容
        plan = re.search(r"<search.*?>(.*?)</search>", match, re.IGNORECASE).group(1)
        extracted_plans.append(plan)
    if len(extracted_plans) == 0:
        return ""
    else:
        return extracted_plans[0].strip()
