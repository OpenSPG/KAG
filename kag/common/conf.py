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
import copy
import os
import logging
import yaml

from pathlib import Path
from typing import Union, Optional

from knext.project.client import ProjectClient


class KAGConstants(object):
    LOCAL_SCHEMA_URL = "http://localhost:8887"
    DEFAULT_KAG_CONFIG_FILE_NAME = "default_config.yaml"
    KAG_CONFIG_FILE_NAME = "kag_config.yaml"
    DEFAULT_KAG_CONFIG_PATH = os.path.join(__file__, DEFAULT_KAG_CONFIG_FILE_NAME)
    KAG_CFG_PREFIX = "KAG"
    GLOBAL_CONFIG_KEY = "global"
    PROJECT_CONFIG_KEY = "project"
    KAG_PROJECT_ID_KEY = "KAG_PROJECT_ID"
    KAG_HOST_ADDR_KEY = "KAG_PROJECT_HOST_ADDR"
    KAG_LANGUAGE_KEY = "KAG_LANGUAGE"
    KAG_BIZ_SCENE_KEY = "KAG_BIZ_SCENE"


class KAGGlobalConf:
    def __init__(self):
        pass

    def setup(self, **kwargs):
        self.project_id = kwargs.pop(KAGConstants.KAG_PROJECT_ID_KEY, "1")
        self.host_addr = kwargs.pop(
            KAGConstants.KAG_HOST_ADDR_KEY, "http://127.0.0.1:8887"
        )
        self.biz_scene = kwargs.pop(KAGConstants.KAG_BIZ_SCENE_KEY, "default")
        self.language = kwargs.pop(KAGConstants.KAG_LANGUAGE_KEY, "en")
        for k, v in kwargs.items():
            setattr(self, k, v)


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
    cfg_file = path / KAGConstants.KAG_CONFIG_FILE_NAME
    if cfg_file.exists():
        return str(cfg_file)
    return _closest_cfg(path.parent, path)


def load_config(prod: bool = False):
    """
    Get kag config file as a ConfigParser.
    """
    if prod:
        project_id = os.getenv(KAGConstants.KAG_PROJECT_ID_KEY)
        host_addr = os.getenv(KAGConstants.KAG_HOST_ADDR_KEY)
        config = ProjectClient(host_addr=host_addr).get_config(project_id)
        return config
    else:
        config_file = _closest_cfg()
        if os.path.exists(config_file) and os.path.isfile(config_file):
            print(f"found config file: {config_file}")
            with open(config_file, "r") as reader:
                config = reader.read()
            return yaml.safe_load(config)
        else:
            return {}


def init_kag_config(config):
    global_config = config.get(KAGConstants.GLOBAL_CONFIG_KEY, {})
    KAG_PROJECT_CONF.setup(**global_config)
    log_conf = config.get("log", {})
    if log_conf:
        log_level = log_conf.get("level", "INFO")
    else:
        log_level = "INFO"
    logging.basicConfig(level=logging.getLevelName(log_level))
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
    logging.getLogger("neo4j.io").setLevel(logging.INFO)
    logging.getLogger("neo4j.pool").setLevel(logging.INFO)


class KAGConfigMgr:
    def __init__(self):
        self.config = {}
        self.global_config = KAGGlobalConf()
        self._is_initialize = False

    def initialize(self, prod: bool = True):
        self.prod = prod
        self.config = load_config(prod)
        global_config = self.config.get(KAGConstants.PROJECT_CONFIG_KEY, {})
        self.global_config.setup(**global_config)
        init_kag_config(self.config)
        self._is_initialize = True

    @property
    def all_config(self):
        return copy.deepcopy(self.config)


KAG_CONFIG = KAGConfigMgr()

KAG_PROJECT_CONF = KAG_CONFIG.global_config


def init_env():
    project_id = os.getenv(KAGConstants.KAG_PROJECT_ID_KEY)
    host_addr = os.getenv(KAGConstants.KAG_HOST_ADDR_KEY)
    if project_id and host_addr:
        prod = True
    else:
        prod = False
    global KAG_CONFIG
    KAG_CONFIG.initialize(prod)

    if prod:
        msg = "Done init config from server"
    else:
        msg = "Done init config from local file"

    print(f"==================={msg}===================")
    import pprint

    pprint.pprint(KAG_CONFIG.all_config, indent=2)
