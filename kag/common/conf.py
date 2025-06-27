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
import json
import pprint
from jinja2 import Template
from pathlib import Path
from typing import Union, Optional

import knext.common.cache
from knext.project.client import ProjectClient

logger = logging.getLogger()


class KAGConstants(object):
    LOCAL_SCHEMA_URL = "http://localhost:8887"
    DEFAULT_KAG_CONFIG_FILE_NAME = "default_config.yaml"
    KAG_CONFIG_FILE_NAME = "kag_config.yaml"
    DEFAULT_KAG_CONFIG_PATH = os.path.join(__file__, DEFAULT_KAG_CONFIG_FILE_NAME)
    KAG_CFG_PREFIX = "KAG"
    GLOBAL_CONFIG_KEY = "global"
    PROJECT_CONFIG_KEY = "project"
    KAG_NAMESPACE_KEY = "namespace"
    KAG_PROJECT_ID_KEY = "id"
    KAG_PROJECT_HOST_ADDR_KEY = "host_addr"
    KAG_LANGUAGE_KEY = "language"
    KAG_USER_TOKEN_KEY = "user_token"
    KAG_CKPT_DIR_KEY = "checkpoint_path"
    KAG_QA_TASK_CONFIG_KEY = "kag_qa_task_config_key"
    KAG_BIZ_SCENE_KEY = "biz_scene"
    ENV_KAG_PROJECT_ID = "KAG_PROJECT_ID"
    ENV_KAG_PROJECT_HOST_ADDR = "KAG_PROJECT_HOST_ADDR"
    ENV_KAG_DEBUG_DUMP_CONFIG = "KAG_DEBUG_DUMP_CONFIG"
    KAG_SIMILAR_EDGE_NAME = "similar"

    KS8_ENV_TF_CONFIG = "TF_CONFIG"
    K8S_ENV_MASTER_ADDR = "MASTER_ADDR"
    K8S_ENV_MASTER_PORT = "MASTER_PORT"
    K8S_ENV_WORLD_SIZE = "WORLD_SIZE"
    K8S_ENV_RANK = "RANK"
    K8S_ENV_POD_NAME = "POD_NAME"


class KAGGlobalConf:
    def __init__(self):
        self._extra = {}

    def initialize(self, **kwargs):
        self.project_id = kwargs.pop(
            KAGConstants.KAG_PROJECT_ID_KEY,
            os.getenv(KAGConstants.ENV_KAG_PROJECT_ID, None),
        )
        self.host_addr = kwargs.pop(
            KAGConstants.KAG_PROJECT_HOST_ADDR_KEY,
            os.getenv(KAGConstants.ENV_KAG_PROJECT_HOST_ADDR, None),
        )
        self.biz_scene = kwargs.pop(KAGConstants.KAG_BIZ_SCENE_KEY, "default")
        self.language = kwargs.pop(KAGConstants.KAG_LANGUAGE_KEY, "en")
        self.namespace = kwargs.pop(KAGConstants.KAG_NAMESPACE_KEY, None)
        self.ckpt_dir = kwargs.pop(KAGConstants.KAG_CKPT_DIR_KEY, "ckpt")
        self.user_token = kwargs.pop(KAGConstants.KAG_USER_TOKEN_KEY, None)
        # process configs set to class attr directly
        for k in self._extra.keys():
            if hasattr(self, k):
                delattr(self, k)

        for k, v in kwargs.items():
            setattr(self, k, v)
        self._extra = kwargs


def _env_parser(loader, node):
    value = loader.construct_scalar(node)
    var_name = value.strip()
    return os.getenv(var_name)


yaml.SafeLoader.add_constructor("!ENV", _env_parser)


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


def validate_config_file(config_file: str):
    if not config_file:
        return False
    if not os.path.exists(config_file):
        return False
    return True


def load_config(prod: bool = False, config_file: str = None):
    """
    Get kag config file as a ConfigParser.
    """
    if prod:
        project_id = os.getenv(KAGConstants.ENV_KAG_PROJECT_ID)
        host_addr = os.getenv(KAGConstants.ENV_KAG_PROJECT_HOST_ADDR)
        project_client = ProjectClient(host_addr=host_addr, project_id=project_id)
        project = project_client.get_by_id(project_id)
        if not project:
            return {}
        config = json.loads(project.config)
        if "project" not in config:
            config["project"] = {
                KAGConstants.KAG_PROJECT_ID_KEY: project_id,
                KAGConstants.KAG_PROJECT_HOST_ADDR_KEY: host_addr,
                KAGConstants.KAG_NAMESPACE_KEY: project.namespace,
            }
            prompt_config = config.pop("prompt", {})
            for key in [KAGConstants.KAG_LANGUAGE_KEY, KAGConstants.KAG_BIZ_SCENE_KEY]:
                if key in prompt_config:
                    config["project"][key] = prompt_config[key]
        if "vectorizer" in config and "vectorize_model" not in config:
            config["vectorize_model"] = config["vectorizer"]
        # host_addr on server may be incorrect, override it.
        config["project"][KAGConstants.KAG_PROJECT_HOST_ADDR_KEY] = host_addr
        return config
    else:
        if not validate_config_file(config_file):
            config_file = _closest_cfg()
        if os.path.exists(config_file) and os.path.isfile(config_file):
            logger.debug(f"found config file: {config_file}")
            with open(config_file, "r") as reader:
                config = reader.read()
                config = Template(config).render(**dict(os.environ))
            return yaml.safe_load(config)
        else:
            return {}


class KAGConfigMgr:
    def __init__(self):
        self.config = {}
        self.global_config = KAGGlobalConf()
        self._is_initialized = False

    def init_log_config(self, config):
        log_conf = config.get("log", {})
        if log_conf:
            log_level = log_conf.get("level", "INFO")
        else:
            log_level = "INFO"
        logging.basicConfig(
            level=logging.getLevelName(log_level),
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
        logging.getLogger("neo4j.io").setLevel(logging.INFO)
        logging.getLogger("neo4j.pool").setLevel(logging.INFO)

    def initialize(self, prod: bool = True, config_file: str = None):
        config = load_config(prod, config_file)
        if self._is_initialized:
            logger.debug("WARN: Reinitialize the KAG configuration.")
            logger.debug(f"original config: {self.config}\n\n")
            logger.debug(f"new config: {config}")
        self.prod = prod
        self.config = config
        global_config = self.config.get(KAGConstants.PROJECT_CONFIG_KEY, {})
        self.global_config.initialize(**global_config)
        self.init_log_config(self.config)
        self._is_initialized = True

    @property
    def all_config(self):
        return copy.deepcopy(self.config)

    def update_conf(self, configs: dict):
        for k, v in configs.items():
            self.config[k] = v


KAG_CONFIG = KAGConfigMgr()

KAG_PROJECT_CONF = KAG_CONFIG.global_config

"""
KAG_QA_TASK_CONFIG stores per-task configuration and should be cleaned up after use.
"""
KAG_QA_TASK_CONFIG = knext.common.cache.LinkCache(maxsize=100, ttl=300)


class KAGConfigAccessor:
    @staticmethod
    def get_default_config():
        if KAG_CONFIG.global_config.project_id:
            return KAG_CONFIG
        for k in KAG_QA_TASK_CONFIG.cache.keys():
            return KAG_QA_TASK_CONFIG.get(k)
        return KAG_CONFIG

    @staticmethod
    def get_config(task_with_kb_id=None) -> KAGConfigMgr:
        """
        Get the configuration information.

        If task_id is provided, retrieve the corresponding config from KAG_QA_TASK_CONFIG;
        otherwise, return the global KAG_CONFIG.

        :param task_with_kb_id: Task ID, optional
        :return: Corresponding configuration object
        """
        if task_with_kb_id is not None:
            return KAG_QA_TASK_CONFIG.get(task_with_kb_id)
        return KAGConfigAccessor.get_default_config()

    @staticmethod
    def set_task_config(task_with_kb_id, config: KAGConfigMgr):
        """
        Set the configuration for a specific task.

        :param task_with_kb_id: Task ID
        :param config: Configuration object to store
        """
        KAG_QA_TASK_CONFIG.put(task_with_kb_id, config)


def init_env(config_file: str = None):
    project_id = os.getenv(KAGConstants.ENV_KAG_PROJECT_ID)
    host_addr = os.getenv(KAGConstants.ENV_KAG_PROJECT_HOST_ADDR)
    prod = False
    if (
        project_id is not None
        and host_addr is not None
        and not validate_config_file(config_file)
    ):
        prod = True
    global KAG_CONFIG
    KAG_CONFIG.initialize(prod, config_file)
    if prod:
        msg = "Done init config from server"
    else:
        msg = "Done init config from local file"
    logger.debug(msg)
    if KAG_PROJECT_CONF.project_id:
        os.environ[KAGConstants.ENV_KAG_PROJECT_ID] = str(KAG_PROJECT_CONF.project_id)
    if KAG_PROJECT_CONF.host_addr:
        os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR] = str(
            KAG_PROJECT_CONF.host_addr
        )
    if len(KAG_CONFIG.all_config) > 0:
        dump_flag = os.getenv(KAGConstants.ENV_KAG_DEBUG_DUMP_CONFIG)
        if dump_flag is not None and dump_flag.strip() == "1":
            pprint.pprint(KAG_CONFIG.all_config, indent=2)
