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


class KAGConstants(object):
    LOCAL_SCHEMA_URL = "http://localhost:8887"
    DEFAULT_KAG_CONFIG_FILE_NAME = "default_config.cfg"
    KAG_CONFIG_FILE_NAME = "kag_config.cfg"
    DEFAULT_KAG_CONFIG_PATH = os.path.join(__file__, DEFAULT_KAG_CONFIG_FILE_NAME)
    KAG_CFG_PREFIX = "KAG"
    GLOBAL_CONFIG_KEY = "global"
    KAG_PROJECT_ID_KEY = "KAG_PROJECT_ID"
    KAG_HOST_ADDR_KEY = "KAG_HOST_ADDR"
    KAG_LANGUAGE_KEY = "KAG_LANGUAGE"


class KAGGlobalConf:
    def __init__(self):
        pass

    def setup(self, **kwargs):
        self.project_id = kwargs.pop(KAGConstants.KAG_PROJECT_ID_KEY, "1")
        self.host_addr = kwargs.pop(
            KAGConstants.KAG_HOST_ADDR_KEY, "http://127.0.0.1:8887"
        )
        self.language = kwargs.pop(KAGConstants.KAG_LANGUAGE_KEY, "en")
        for k, v in kwargs.items():
            setattr(self, k, v)


KAG_GLOBAL_CONF = KAGGlobalConf()
