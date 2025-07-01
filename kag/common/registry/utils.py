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

import os
import sys
import importlib
import pkgutil
from pathlib import Path
from typing import Union


def append_python_path(path: Union[os.PathLike, str]) -> None:
    """
    Append the given path to `sys.path`.
    """
    # In some environments, such as TC, it fails when sys.path contains a relative path, such as ".".
    path = Path(path).resolve()
    path = str(path)
    sys.path.insert(0, path)


def import_modules_from_path(path: str) -> None:
    """
    Import all submodules under the given package.
    User can specify their custom packages and have their custom
    classes get loaded and registered.
    """
    path = os.path.abspath(os.path.normpath(path))
    importlib.invalidate_caches()
    tmp = path.rsplit(os.sep, 1)
    if len(tmp) == 1:
        module_path = "."
        package_name = tmp[0]
    else:
        module_path, package_name = tmp
    append_python_path(module_path)
    # Import at top level
    module = importlib.import_module(package_name)
    path = list(getattr(module, "__path__", []))
    path_string = "" if not path else path[0]
    # walk_packages only finds immediate children, so need to recurse.
    for module_finder, name, _ in pkgutil.walk_packages(path):
        # Sometimes when you import third-party libraries that are on your path,
        # `pkgutil.walk_packages` returns those too, so we need to skip them.
        if path_string and module_finder.path != path_string:
            continue
        # subpackage = f"{package_name}.{name}"
        subpackage = f"{path_string}/{name}"

        import_modules_from_path(subpackage)
