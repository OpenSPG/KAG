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
                logging.basicConfig(level=logging.getLevelName(value))
            except:
                logger.info("logger info not set")
        return cls._instance

    @property
    def config(self):
        if self._config is None:
            self._config = self.get_config()
        if self._config != self.get_config():
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f)
        return self._config

    @property
    def project_path(self):
        config_path = self._closest_config()
        return os.path.abspath(os.path.dirname(config_path))

    @property
    def config_path(self):
        return self._closest_config()

    @property
    def project_config(self):
        return self.config.get("project", {})

    @property
    def id(self):
        if os.getenv("KAG_PROJECT_ID"):
            return os.getenv("KAG_PROJECT_ID")
        id = self.project_config.get("id", None)
        if id is None:
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
        if os.getenv("KAG_PROJECT_HOST_ADDR"):
            return os.getenv("KAG_PROJECT_HOST_ADDR")
        host_addr = self.project_config.get("host_addr", None)
        if host_addr is None:
            host_addr = DEFAULT_HOST_ADDR
            logger.warning(f"project host_addr is not defined, use default host_addr: {host_addr}")
        return host_addr

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
        Return the path to the closest .knext.cfg file by traversing the current
        directory and its parents
        """
        if prev_path is not None and str(path) == str(prev_path):
            return ""
        path = Path(path).resolve()
        cfg_file = path / "kag_config.yaml"
        if cfg_file.exists():
            return str(cfg_file)
        return self._closest_config(path.parent, path)

    def dump(self, path=None, **kwargs):
        with open(path or self.config_path, "w") as f:
            yaml.dump(self.config, f, **kwargs)


env = Environment()
