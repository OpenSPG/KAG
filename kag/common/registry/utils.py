# -*- coding: utf-8 -*-
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
    sys.path.append(path)


def import_modules_from_path(path: str) -> None:
    """
    Import all submodules under the given package.
    User can specify their custom packages and have their custom
    classes get loaded and registered.
    """
    importlib.invalidate_caches()
    tmp = path.rsplit("/", 1)
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
