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
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
import kag.interface as interface
from kag.interface.common.llm_client import LLMCallCcontext, TokenMeterFactory
from kag.common.conf import KAGConstants, init_env
from kag.indexer.kag_index_manager import KAGIndexManager


import logging

logger = logging.getLogger(__name__)


def init_kag_config(project_id: str, host_addr: str):
    os.environ[KAGConstants.ENV_KAG_PROJECT_ID] = project_id
    os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR] = host_addr
    init_env()


def collect_reader_outputs(data):
    chunks = []
    subgraphs = []

    def collect(data):
        from kag.interface.builder.base import BuilderComponentData

        if isinstance(data, BuilderComponentData):
            chunks.append(data)
        elif isinstance(data, Chunk):
            chunks.append(data)
        elif isinstance(data, SubGraph):
            subgraphs.append(data)
        elif isinstance(data, (tuple, list)):
            for item in data:
                collect(item)
        else:
            logger.debug(
                f"expect Chunk and SubGraph nested in tuple and list; found {data.__class__}"
            )

    collect(data)
    return chunks, subgraphs


class SPGServerBridge:
    def __init__(self):
        pass

    def run_scanner(self, config, input_data):
        if isinstance(config, str):
            config = json.loads(config)
        scanner_config = config["scanner"]
        scanner = interface.ScannerABC.from_config(scanner_config)
        output = []
        for data in scanner.generate(input_data):
            output.append(data)
        return output

    def run_reader(self, config, input_data):
        try:
            if isinstance(config, str):
                config = json.loads(config)
            scanner_config = config["scanner"]
            reader_config = config["reader"]
            scanner = interface.ScannerABC.from_config(scanner_config)
            reader = interface.ReaderABC.from_config(reader_config)
            chunks = []
            for data in scanner.generate(input_data):
                reader_output = reader.invoke(data, write_ckpt=False)
                chunk, _ = collect_reader_outputs(reader_output)
                chunks += chunk
            return [x.to_dict() for x in chunks]
        except Exception as e:
            import traceback

            msg = f"Failed to run Reader with config {config}, detail info:\n{traceback.format_exc()}"
            logger.error(f"===================\n{msg}===================")
            raise e

    def run_component(self, component_name, component_config, input_data):
        if isinstance(component_config, str):
            component_config = json.loads(component_config)
        task_id = component_config.get("task_id", "0")
        with LLMCallCcontext(task_id=task_id, token_meter_in_memory=False):
            try:
                cls = getattr(interface, component_name)
                instance = cls.from_config(component_config)
                if not isinstance(input_data, list):
                    input_data = [input_data]
                output = []
                for item in input_data:
                    if hasattr(instance.input_types, "from_dict"):
                        item = instance.input_types.from_dict(item)
                    output.extend(
                        [x.to_dict() for x in instance.invoke(item, write_ckpt=False)]
                    )
                return output
            except Exception as e:
                import traceback

                msg = f"Failed to run component {component_name} with config {component_config}, detail info:\n{traceback.format_exc()}"
                logger.error(f"===================\n{msg}===================")
                raise e

    def run_llm_config_check(self, llm_config):
        from kag.common.llm.llm_config_checker import LLMConfigChecker

        return LLMConfigChecker().check(llm_config)

    def run_vectorizer_config_check(self, vec_config):
        from kag.common.vectorize_model.vectorize_model_config_checker import (
            VectorizeModelConfigChecker,
        )

        return VectorizeModelConfigChecker().check(vec_config)

    def run_builder(self, config, input):
        if isinstance(config, str):
            config = json.loads(config)
        task_id = config.get("task_id" "0")
        with LLMCallCcontext(task_id=task_id, token_meter_in_memory=False):
            from kag.builder.main_builder import BuilderMain

            builder_main = BuilderMain(config)
            builder_main.invoke(input)

    def run_solver(
        self,
        project_id,
        session_id,
        task_id,
        query,
        args,
        func_name="invoke",
        is_report=True,
        host_addr="http://127.0.0.1:8887",
        app_id="",
    ):
        with LLMCallCcontext(task_id=task_id, token_meter_in_memory=False):
            from kag.solver.main_solver import SolverMain

            if isinstance(args, str):
                args = json.loads(args)
            params = args.get("args", {})
            print(f"run_solver {func_name} args: {params} {args}")
            return getattr(SolverMain(), func_name)(
                project_id=project_id,
                session_id=session_id,
                task_id=task_id,
                query=query,
                is_report=is_report,
                host_addr=host_addr,
                params=params,
                app_id=app_id,
            )

    def get_llm_token_info(self, task_id):
        factory = TokenMeterFactory()
        token_meter = factory.get_meter(task_id)
        data = token_meter.to_dict()
        factory.remove_meter(task_id)
        return data

    def get_index_manager_info(
        self, index_manager_name, llm_config, vectorize_model_config
    ):
        if isinstance(llm_config, str):
            llm_config = json.loads(llm_config)
        if isinstance(vectorize_model_config, str):
            vectorize_model_config = json.loads(vectorize_model_config)
        config = {
            "type": index_manager_name,
            "llm_config": llm_config,
            "vectorize_model_config": vectorize_model_config,
        }

        index_mgr = KAGIndexManager.from_config(config)
        meta = index_mgr.get_meta()
        return json.dumps(meta, ensure_ascii=False)

    def get_index_manager_names(self):
        return KAGIndexManager.list_available_with_detail()


if __name__ == "__main__":
    config = {"reader": {"cut_depth": 3, "type": "md"}, "scanner": {"type": "file"}}
    bridge = SPGServerBridge()
    res = bridge.run_reader(
        config, "/Users/zhangxinhong.zxh/Downloads/baike-person-zhoujielun.md"
    )
    print(res)
