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
import logging
import os
import sys
from configparser import ConfigParser as CP
from pathlib import Path
from typing import Union, Optional

import kag.common as common

class ConfigParser(CP):
    def __init__(self,defaults=None):
        CP.__init__(self,defaults=defaults)
    def optionxform(self, optionstr):
        return optionstr


LOCAL_SCHEMA_URL = "http://localhost:8887"
DEFAULT_KAG_CONFIG_FILE_NAME = "default_config.cfg"
DEFAULT_KAG_CONFIG_PATH = os.path.join(common.__path__[0], DEFAULT_KAG_CONFIG_FILE_NAME)
KAG_CFG_PREFIX = "KAG"


def init_env():
    """Initialize environment to use command-line tool from inside a project
    dir. This sets the Scrapy settings module and modifies the Python path to
    be able to locate the project module.
    """
    project_cfg, root_path = get_config()

    init_kag_config(Path(root_path) / "kag_config.cfg")


def get_config():
    """
    Get kag config file as a ConfigParser.
    """
    local_cfg_path = _closest_cfg()
    local_cfg = ConfigParser()
    local_cfg.read(local_cfg_path)

    projdir = ""
    if local_cfg_path:
        projdir = str(Path(local_cfg_path).parent)
        if projdir not in sys.path:
            sys.path.append(projdir)

    return local_cfg, projdir


def _closest_cfg(
    path: Union[str, os.PathLike] = ".",
    prev_path: Optional[Union[str, os.PathLike]] = None,
) -> str:
    """
    Return the path to the closest .kag.cfg file by traversing the current
    directory and its parents
    """
    if prev_path is not None and str(path) == str(prev_path):
        return ""
    path = Path(path).resolve()
    cfg_file = path / "kag_config.cfg"
    if cfg_file.exists():
        return str(cfg_file)
    return _closest_cfg(path.parent, path)


def get_cfg_files():
    """
    Get global and local kag config files and paths.
    """
    local_cfg_path = _closest_cfg()
    local_cfg = ConfigParser()
    local_cfg.read(local_cfg_path)

    if local_cfg_path:
        projdir = str(Path(local_cfg_path).parent)
        if projdir not in sys.path:
            sys.path.append(projdir)

    return local_cfg, local_cfg_path



def init_kag_config(config_path: Union[str, Path] = None):
    if not config_path or isinstance(config_path, Path) and not config_path.exists():
        config_path = DEFAULT_KAG_CONFIG_PATH
    kag_cfg = ConfigParser()
    kag_cfg.read(config_path)
    os.environ["KAG_PROJECT_ROOT_PATH"] = os.path.abspath(os.path.dirname(config_path))

    for section in kag_cfg.sections():
        sec_cfg = {}
        for key, value in kag_cfg.items(section):
            item_cfg_key = f"{KAG_CFG_PREFIX}_{section}_{key}".upper()
            os.environ[item_cfg_key] = value
            sec_cfg[key] = value
        sec_cfg_key = f"{KAG_CFG_PREFIX}_{section}".upper()
        os.environ[sec_cfg_key] = str(sec_cfg)
        if section == "log":
            for key, value in kag_cfg.items(section):
                if key == "level":
                    logging.basicConfig(level=logging.getLevelName(value))
                    # neo4j log level set to be default error
                    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
                    logging.getLogger("neo4j.io").setLevel(logging.INFO)
                    logging.getLogger("neo4j.pool").setLevel(logging.INFO)
