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
import asyncio
import logging
import json
import os
import re
import copy

import yaml

from kag.interface import SolverPipelineABC

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.solver.reporter.open_spg_reporter import OpenSPGReporter


logger = logging.getLogger()

def get_all_placeholders(config, placeholders):
    if isinstance(config, dict):
        for key, value in config.items():
            get_all_placeholders(value, placeholders)
    elif isinstance(config, list):
        return [get_all_placeholders(item, placeholders) for item in config]
    elif isinstance(config, str):
        if config.startswith("{") and config.endswith("}"):
            placeholder = config[1:-1]  # 去掉花括号
            placeholders.append(placeholder)
        return config
    else:
        return config

def replace_placeholders(config, replacements):
    if isinstance(config, dict):
        return {
            key: replace_placeholders(value, replacements)
            for key, value in config.items()
        }
    elif isinstance(config, list):
        return [replace_placeholders(item, replacements) for item in config]
    elif isinstance(config, str):
        if config.startswith("{") and config.endswith("}"):
            placeholder = config[1:-1]  # 去掉花括号
            if placeholder in replacements:
                return replacements[placeholder]
            else:
                raise RuntimeError(f"Placeholder '{placeholder}' not found in config.")
        return config
    else:
        return config


def load_yaml_files_from_conf_dir():

    current_dir = os.path.dirname(os.path.abspath(__file__))

    conf_dir = os.path.join(current_dir, 'pipelineconf')


    if not os.path.exists(conf_dir) or not os.path.isdir(conf_dir):
        raise FileNotFoundError(f"The 'conf' directory does not exist at {conf_dir}")


    yaml_data = {}


    for filename in os.listdir(conf_dir):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            file_path = os.path.join(conf_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as file:

                yaml_content = yaml.safe_load(file)
                yaml_data[yaml_content["pipeline_name"]] = yaml_content

    return yaml_data

def get_pipeline_conf(use_pipeline_name, config):
    pipeline_name = "solver_pipeline"
    conf_map = load_yaml_files_from_conf_dir()
    if use_pipeline_name not in conf_map:
        raise RuntimeError(f"Pipeline configuration not found for pipeline_name: {use_pipeline_name}")

    placeholders = []
    get_all_placeholders(conf_map[use_pipeline_name], placeholders)
    placeholders = list(set(placeholders))
    placeholders_replacement_map = {}
    for placeholder in placeholders:
        value = config.get(placeholder)
        backup_key = None
        if value is None:
            if "llm" in placeholder:
                backup_key = "llm"
            if "vectorizer" in placeholder:
                backup_key = "vectorizer"
            if backup_key:
                value = config.get(backup_key)
        if value is None:
            raise RuntimeError(f"Placeholder '{placeholder}' '{'or '+backup_key if backup_key else ''}' not found in config.")
        value["enable_check"] = False
        placeholders_replacement_map[placeholder] = value
    default_pipeline_conf = replace_placeholders(conf_map[use_pipeline_name], placeholders_replacement_map)
    default_solver_pipeline = default_pipeline_conf[pipeline_name]

    if use_pipeline_name == "mcp_pipeline":
        mcp_servers = config.get("mcpServers", None)
        mcp_executors = []
        if mcp_servers is not None:
            for mcp_name, mcp_conf in mcp_servers.items():
                desc = mcp_conf["description"]
                env = mcp_conf["env"]
                store_path = mcp_conf["store_path"]
                mcp_executors.append(
                    {
                        "type": "mcp_executor",
                        "store_path": store_path,
                        "name": mcp_name,
                        "description": desc,
                        "env": env,
                        "llm": config.get("llm"),
                    }
                )
        else:
            raise RuntimeError("mcpServers not found in config.")
        default_solver_pipeline["executors"] = mcp_executors

    # update KAG_CONFIG
    KAG_CONFIG.update_conf(default_pipeline_conf)
    return default_solver_pipeline

def is_chinese(text):
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))

async def qa(task_id, query, project_id, host_addr, params={}):
    use_pipeline = params.get("usePipeline", "think_pipeline")
    qa_config = params.get("config", KAG_CONFIG.all_config)
    if isinstance(qa_config, str):
        qa_config = json.loads(qa_config)
    print(f"qa_config = {json.dumps(qa_config, ensure_ascii=False, indent=2)}")
    thinking_enabled = use_pipeline == "think_pipeline"
    print(
        f"qa(task_id={task_id}, query={query}, project_id={project_id}, use_pipeline={use_pipeline}, params={params})"
    )
    reporter: OpenSPGReporter = OpenSPGReporter(
        task_id=task_id,
        host_addr=host_addr,
        project_id=project_id,
        thinking_enabled=thinking_enabled,
    )
    await reporter.start()
    try:
        if is_chinese(query):
            KAG_PROJECT_CONF.language = "zh"
        else:
            KAG_PROJECT_CONF.language = "en"

        custom_pipeline_conf = copy.deepcopy(KAG_CONFIG.all_config.get("solver_pipeline", None))
        # self cognition
        self_cognition_conf = get_pipeline_conf("self_cognition_pipeline", qa_config)
        self_cognition_pipeline = SolverPipelineABC.from_config(self_cognition_conf)
        self_cognition_res = await self_cognition_pipeline.ainvoke(query, reporter=reporter)
        if not self_cognition_res:
            if custom_pipeline_conf:
                pipeline_config = custom_pipeline_conf
            else:
                pipeline_config = get_pipeline_conf(use_pipeline, qa_config)
            logger.error(f"pipeline conf: \n{pipeline_config}")
            pipeline = SolverPipelineABC.from_config(pipeline_config)
            answer = await pipeline.ainvoke(query, reporter=reporter)
        else:
            answer = self_cognition_res
    except Exception as e:
        logger.warning(
            f"An exception occurred while processing query: {query}. Error: {str(e)}",
            exc_info=True,
        )
        if KAG_PROJECT_CONF.language == "en":
            answer = f"Sorry, An exception occurred while processing query: {query}. Error: {str(e)}, please retry."
        else:
            answer = f"抱歉，处理查询 {query} 时发生异常。错误：{str(e)}, 请重试。"
        reporter.add_report_line("answer", "error", answer, "ERROR")
    await reporter.stop()
    return answer


class SolverMain:
    def invoke(
        self,
        project_id: int,
        task_id: int,
        query: str,
        session_id: str = "0",
        is_report=True,
        host_addr="http://127.0.0.1:8887",
        params=None,
    ):
        answer = None
        if params is None:
            params = {}
        try:
            answer = asyncio.run(
                qa(
                    task_id=task_id,
                    project_id=project_id,
                    host_addr=host_addr,
                    query=query,
                    params=params,
                )
            )
            logger.info(f"{query} answer={answer}")
        except Exception as e:
            import traceback

            traceback.print_exc()
            logger.warning(
                f"An exception occurred while processing query: {query}. Error: {str(e)}",
                exc_info=True,
            )
        return answer


if __name__ == "__main__":
    from kag.bridge.spg_server_bridge import init_kag_config

    init_kag_config(
        "4200041", "http://127.0.0.1:8887"
    )
    res = SolverMain().invoke(
        4200041,
        6300136,
        "Talk about Jay Zhou",
        "4700026",
        True,
        host_addr="http://127.0.0.1:8887",
    )
    print("*" * 80)
    print("The Answer is: ", res)
