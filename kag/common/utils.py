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
import re
import sys
import json
import hashlib
import os
import tempfile
import requests
import importlib
from typing import Tuple
from pathlib import Path

from shutil import copystat, copy2
from typing import Any, Union
from jinja2 import Environment, FileSystemLoader, Template
from stat import S_IWUSR as OWNER_WRITE_PERMISSION
from tenacity import retry, stop_after_attempt

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
        Tuple[str, Any]: A tuple containing the hash ID and the abstracted value.
    """
    if isinstance(value, dict):
        sorted_items = sorted(value.items())
        key = str(sorted_items)
    else:
        key = value
    if isinstance(key, str):
        key = key.encode("utf-8")
    hasher = hashlib.sha256()
    hasher.update(key)

    return hasher.hexdigest()


@retry(stop=stop_after_attempt(3))
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
