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
from collections import OrderedDict
import logging
import os
import sys
import json
from ruamel.yaml import YAML
from pathlib import Path
from typing import Union, Optional

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)
logger = logging.getLogger(__name__)

DEFAULT_HOST_ADDR = "http://127.0.0.1:8887"


class Environment:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Environment, cls).__new__(cls)
            try:
                log_config = cls._instance.config.get("log", {})
                value = log_config.get("level", "INFO")
                logging.basicConfig(
                    level=logging.getLevelName(value),
                    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            except:
                logger.info("logger info not set")
        return cls._instance

    @property
    def config(self):

        closest_config = self._closest_config()
        if not hasattr(self, "_config_path") or self._config_path != closest_config:
            self._config_path = closest_config
            self._config = self.get_config()

        if self._config is None:
            self._config = self.get_config()

        return self._config

    @property
    def project_path(self):
        config_path = self._closest_config()
        return os.path.abspath(os.path.dirname(config_path))

    @property
    def config_path(self):
        if not hasattr(self, "_config_path") or self._config_path is None:
            self._config_path = self._closest_config()
        return self._config_path

    @property
    def project_config(self):
        return self.config.get("project", {})

    @property
    def id(self):

        id = self.project_config.get("id", None)
        if id is None:
            logger.warning("can not find id in project config")
            if os.getenv("KAG_PROJECT_ID", None):
                return os.getenv("KAG_PROJECT_ID")
            else:
                raise Exception(
                    "project id not restore in spgserver, please restore project first"
                )
        return id

    @property
    def project_id(self):
        return self.id

    @property
    def namespace(self):
        if os.getenv("KAG_PROJECT_NAMESPACE"):
            return os.getenv("KAG_PROJECT_NAMESPACE")
        namespace = self.project_config.get("namespace", None)
        if namespace is None:
            raise Exception("project namespace is not defined")
        return namespace

    @property
    def name(self):
        return self.namespace

    @property
    def host_addr(self):
        return self.project_config.get("host_addr", None)

    def get_config(self):
        """
        Get knext config file as a ConfigParser.
        """
        local_cfg_path = self._closest_config()
        try:
            with open(local_cfg_path) as f:
                local_cfg = yaml.load(f)
        except Exception as e:
            raise Exception(f"failed to load config from {local_cfg_path}, error: {e}")
        projdir = ""
        if local_cfg_path:
            projdir = str(Path(local_cfg_path).parent)
            if projdir not in sys.path:
                sys.path.append(projdir)

        return local_cfg

    def _closest_config(
        self,
        path: Union[str, os.PathLike] = ".",
        prev_path: Optional[Union[str, os.PathLike]] = None,
    ) -> str:
        """
        Return the path to the closest kag_config.yaml file by traversing the current
        directory and its parents
        """
        if prev_path is not None and str(path) == str(prev_path):
            return ""
        path = Path(path).resolve()
        cfg_files = list(path.glob("*.yaml"))
        cfg_file = next(
            (f for f in cfg_files if f.name == "kag_config.yaml"),
            cfg_files[0] if cfg_files else None,
        )
        if cfg_file and cfg_file.exists():
            return str(cfg_file)
        if path.parent == path:
            raise FileNotFoundError(
                "No kag_config.yaml file found in current directory or any parent directories"
            )
        return self._closest_config(path.parent, path)

    def dump(self, path=None, **kwargs):
        with open(path or self._config_path, "w", encoding="utf-8", newline="\n") as f:
            yaml.dump(self._config, f)


env = Environment()
