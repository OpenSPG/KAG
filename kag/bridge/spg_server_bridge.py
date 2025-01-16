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
import json
import kag.interface as interface
from kag.common.conf import KAGConstants, init_env


def init_kag_config(project_id: str, host_addr: str):
    os.environ[KAGConstants.ENV_KAG_PROJECT_ID] = project_id
    os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR] = host_addr
    init_env()


class SPGServerBridge:
    def __init__(self):
        pass

    def run_reader(self, config, input_data):
        if isinstance(config, str):
            config = json.loads(config)
        scanner_config = config["scanner"]
        reader_config = config["reader"]
        scanner = interface.ScannerABC.from_config(scanner_config)
        reader = interface.ReaderABC.from_config(reader_config)
        chunks = []
        for data in scanner.generate(input_data):
            chunks += reader.invoke(data, write_ckpt=False)
        return [x.to_dict() for x in chunks]

    def run_component(self, component_name, component_config, input_data):
        if isinstance(component_config, str):
            component_config = json.loads(component_config)

        cls = getattr(interface, component_name)
        instance = cls.from_config(component_config)
        if hasattr(instance.input_types, "from_dict"):
            input_data = instance.input_types.from_dict(input_data)
        return [x.to_dict() for x in instance.invoke(input_data, write_ckpt=False)]

    def run_llm_config_check(self, llm_config):
        from kag.common.llm.llm_config_checker import LLMConfigChecker

        return LLMConfigChecker().check(llm_config)

    def run_vectorizer_config_check(self, vec_config):
        from kag.common.vectorize_model.vectorize_model_config_checker import (
            VectorizeModelConfigChecker,
        )

        return VectorizeModelConfigChecker().check(vec_config)

    def run_solver(
        self,
        project_id,
        task_id,
        query,
        func_name="invoke",
        is_report=True,
        host_addr="http://127.0.0.1:8887",
    ):
        from kag.solver.main_solver import SolverMain

        return getattr(SolverMain(), func_name)(
            project_id=project_id,
            task_id=task_id,
            query=query,
            is_report=is_report,
            host_addr=host_addr,
        )
