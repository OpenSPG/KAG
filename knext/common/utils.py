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
from typing import Type, Tuple
import inspect
import os
from pathlib import Path
import importlib
from shutil import copystat, copy2
from typing import Any, Union
from jinja2 import Environment, FileSystemLoader, Template
from stat import S_IWUSR as OWNER_WRITE_PERMISSION


def _register(root, path, files, class_type):
    relative_path = os.path.relpath(path, root)
    module_prefix = relative_path.replace(".", "").replace("/", ".")
    module_prefix = module_prefix + "." if module_prefix else ""
    for file_name in files:
        if file_name.endswith(".py"):
            module_name = module_prefix + os.path.splitext(file_name)[0]
            import importlib

            module = importlib.import_module(module_name)
            classes = inspect.getmembers(module, inspect.isclass)
            for class_name, class_obj in classes:
                if (
                    issubclass(class_obj, class_type)
                    and inspect.getmodule(class_obj) == module
                ):

                    class_type.register(
                        name=class_name,
                        local_path=os.path.join(path, file_name),
                        module_path=module_name,
                    )(class_obj)


def register_from_package(path: str, class_type: Type) -> None:
    """
    Register all classes under the given package.
    Only registered classes can be recognized by knext.
    """
    if not append_python_path(path):
        return
    for root, dirs, files in os.walk(path):
        _register(path, root, files, class_type)
    class_type._has_registered = True


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
    path_obj = Path(root_dir) / file
    env = Environment(loader=FileSystemLoader(path_obj.parent))
    template = env.get_template(path_obj.name)
    content = template.render(kwargs)

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
