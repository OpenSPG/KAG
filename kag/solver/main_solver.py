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

    conf_dir = os.path.join(current_dir, "pipelineconf")

    if not os.path.exists(conf_dir) or not os.path.isdir(conf_dir):
        raise FileNotFoundError(f"The 'conf' directory does not exist at {conf_dir}")

    yaml_data = {}

    for filename in os.listdir(conf_dir):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            file_path = os.path.join(conf_dir, filename)
            with open(file_path, "r", encoding="utf-8") as file:

                yaml_content = yaml.safe_load(file)
                yaml_data[yaml_content["pipeline_name"]] = yaml_content

    return yaml_data


def get_pipeline_conf(use_pipeline_name, config):
    pipeline_name = "solver_pipeline"
    conf_map = load_yaml_files_from_conf_dir()
    if use_pipeline_name not in conf_map:
        raise RuntimeError(
            f"Pipeline configuration not found for pipeline_name: {use_pipeline_name}"
        )

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
            raise RuntimeError(
                f"Placeholder '{placeholder}' '{'or '+backup_key if backup_key else ''}' not found in config."
            )
        value["enable_check"] = False
        placeholders_replacement_map[placeholder] = value
    default_pipeline_conf = replace_placeholders(
        conf_map[use_pipeline_name], placeholders_replacement_map
    )
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
    chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
    return bool(chinese_pattern.search(text))


async def qa(task_id, query, project_id, host_addr, app_id, params={}):
    use_pipeline = params.get("usePipeline", "think_pipeline")
    qa_config = params.get("config")
    if isinstance(qa_config, str):
        qa_config = json.loads(qa_config)
    logger.info(f"qa_config = {json.dumps(qa_config, ensure_ascii=False, indent=2)}")
    thinking_enabled = use_pipeline == "think_pipeline"
    logger.info(
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

        KAG_PROJECT_CONF.host_addr = host_addr
        KAG_PROJECT_CONF.project_id = qa_config["kb"][0]["id"]
        use_pipeline = qa_config["chat"]["ename"]
        qa_config["vectorize_model"] = qa_config["kb"][0]["vectorizer"]

        custom_pipeline_conf = copy.deepcopy(
            KAG_CONFIG.all_config.get("solver_pipeline", None)
        )
        # self cognition
        self_cognition_conf = get_pipeline_conf("self_cognition_pipeline", qa_config)
        self_cognition_pipeline = SolverPipelineABC.from_config(self_cognition_conf)
        self_cognition_res = await self_cognition_pipeline.ainvoke(
            query, reporter=reporter
        )
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
            answer = f"抱歉，处理查询 {query} 时发生异常。错误：{str(e)}, 请重试。with qa_config={qa_config},pipeline_config={pipeline_config}"
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
        app_id="",
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
                    app_id=app_id,
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

    # init_kag_config(
    #     "4200052", "https://spg-pre.alipay.com"
    # )
    params = {
        "usePipeline": "think_pipeline",
        "config": {
            "chat": {
                "ename": "default_pipeline",
                "cname": "简单问答",
                "logo": "/img/logo/modal_1.png",
                "description": "这是KAG的简单问答模板，不支持深度思考和联网搜索",
                "id": 1,
            },
            "kb": [
                {
                    "mcp_servers": {},
                    "vectorizer": {
                        "modelId": "117b7298ac174c3d979574b66d2a76d9@BAAI/bge-m3",
                        "api_key": "sk-omwqjedsfukilijdqtrbfunsuaslauuyxtamspgyylhlgdih",
                        "vector_dimensions": "768",
                        "base_url": "https://api.siliconflow.cn/v1",
                        "source_type": "custom",
                        "model": "netease-youdao/bce-embedding-base_v1",
                        "modelType": "embedding",
                        "type": "openai",
                    },
                    "visibility": "PRIVATE",
                    "name": "测试构建",
                    "namespace": "Nmt",
                    "description": "",
                    "graph_store": {
                        "database": "nmt",
                        "password": "neo4j@openspg",
                        "uri": "neo4j://6.3.176.118:7687",
                        "user": "neo4j",
                    },
                    "id": 5500004,
                    "tag": "LOCAL",
                    "label": "测试构建",
                    "value": 5500004,
                    "prompt": {"language": "zh"},
                }
            ],
            "language": "en",
            "llm": {
                "visibility": "PUBLIC_READ",
                "modelId": "1d9ea66f5ae443a0b1a8151502a34ee9@deepseek-chat",
                "provider": "DeepSeek",
                "api_key": "sk-5539c76668f44a27adbae3dbb17bfb3b",
                "stream": "False",
                "name": "deepseek-chat",
                "base_url": "https://api.deepseek.com/beta",
                "temperature": 0.7,
                "model": "deepseek-chat",
                "modelType": "chat",
                "type": "maas",
            },
        },
    }
    params = {
        "usePipeline": "default_pipeline",
        "config": {
            "chat": {
                "ename": "think_pipeline",
                "cname": "简单问答",
                "logo": "/img/logo/modal_1.png",
                "description": "这是KAG的简单问答模板，不支持深度思考和联网搜索",
                "id": 1,
            },
            "kb": [
                {
                    "mcp_servers": {},
                    "vectorizer": {
                        "modelId": "117b7298ac174c3d979574b66d2a76d9@BAAI/bge-m3",
                        "api_key": "sk-omwqjedsfukilijdqtrbfunsuaslauuyxtamspgyylhlgdih",
                        "vector_dimensions": "768",
                        "base_url": "https://api.siliconflow.cn/v1",
                        "source_type": "custom",
                        "model": "netease-youdao/bce-embedding-base_v1",
                        "modelType": "embedding",
                        "type": "openai",
                    },
                    "visibility": "PRIVATE",
                    "name": "测试构建",
                    "namespace": "Nmt",
                    "description": "",
                    "graph_store": {
                        "database": "nmt",
                        "password": "neo4j@openspg",
                        "uri": "neo4j://6.3.176.118:7687",
                        "user": "neo4j",
                    },
                    "id": 5500004,
                    "tag": "LOCAL",
                    "label": "测试构建",
                    "value": 5500004,
                    "prompt": {"language": "zh"},
                }
            ],
            "language": "zh",
            "llm": {
                "visibility": "PUBLIC_READ",
                "modelId": "1d9ea66f5ae443a0b1a8151502a34ee9@deepseek-chat",
                "provider": "DeepSeek",
                "api_key": "sk-5539c76668f44a27adbae3dbb17bfb3b",
                "stream": "False",
                "name": "deepseek-chat",
                "base_url": "https://api.deepseek.com/beta",
                "temperature": 0.7,
                "model": "deepseek-chat",
                "modelType": "chat",
                "type": "maas",
            },
        },
    }
    params = {
        "config": {
            "chat": {
                "ename": "think_pipeline",
                "thinking_enabled": True,
                "cname": "推理问答",
                "logo": "/img/logo/modal_2.png",
                "description": "基于蚂蚁集团开源的专业领域知识服务框架KAG搭建的问答模板，擅长逻辑推理、数值计算等任务，可以协助解答相关问题、提供信息支持或进行数据分析",
                "id": 2,
            },
            "kb": [
                {
                    "vectorizer": {
                        "modelId": "117b7298ac174c3d979574b66d2a76d9@BAAI/bge-m3",
                        "api_key": "sk-omwqjedsfukilijdqtrbfunsuaslauuyxtamspgyylhlgdih",
                        "base_url": "https://api.siliconflow.cn/v1",
                        "source_type": "custom",
                        "model": "BAAI/bge-m3",
                        "modelType": "embedding",
                        "type": "openai",
                        "enable_check": False,
                    },
                    # "vectorizer": {
                    #     "modelId": "117b7298ac174c3d979574b66d2a76d9@BAAI/bge-m3",
                    #     "api_key": "sk-omwqjedsfukilijdqtrbfunsuaslauuyxtamspgyylhlgdih",
                    #     "vector_dimensions": "768",
                    #     "base_url": "https://api.siliconflow.cn/v1",
                    #     "source_type": "custom",s
                    #     "model": "netease-youdao/bce-embedding-base_v1",
                    #     "modelType": "embedding",
                    #     "type": "openai",
                    # },
                    "visibility": "PUBLIC_READ",
                    "name": "田常测试1",
                    "namespace": "TcTest1",
                    "description": "",
                    "graph_store": {
                        "database": "tctest1",
                        "password": "neo4j@openspg",
                        "uri": "neo4j://6.3.176.118:7687",
                        "user": "neo4j",
                    },
                    "id": 5800002,
                    "tag": "LOCAL",
                    "label": "田常测试1",
                    "value": 5800002,
                    "prompt": {"language": "zh"},
                }
            ],
            "language": "zh",
            "llm": {
                "visibility": "PUBLIC_READ",
                "modelId": "1d9ea66f5ae443a0b1a8151502a34ee9@deepseek-chat",
                "provider": "DeepSeek",
                "api_key": "sk-5539c76668f44a27adbae3dbb17bfb3b",
                "stream": "False",
                "name": "deepseek-chat",
                "base_url": "https://api.deepseek.com/beta",
                "temperature": 0.7,
                "model": "deepseek-chat",
                "modelType": "chat",
                "type": "maas",
                "enable_check": False,
            },
            "vectorize_model": {
                "modelId": "117b7298ac174c3d979574b66d2a76d9@BAAI/bge-m3",
                "api_key": "sk-omwqjedsfukilijdqtrbfunsuaslauuyxtamspgyylhlgdih",
                "base_url": "https://api.siliconflow.cn/v1",
                "source_type": "custom",
                "model": "BAAI/bge-m3",
                "modelType": "embedding",
                "type": "openai",
                "enable_check": False,
            },
        }
    }
    res = SolverMain().invoke(
        4200052,
        7700089,
        # "阿里巴巴2024年截止到9月30日的总收入是多少元？ 如果把这笔钱于当年10月3日存入银行并于12月29日取出，银行日利息是万分之0.9，本息共可取出多少元？",
        "肝硬化的原因都有哪些呢",
        "4700026",
        True,
        host_addr="http://6.1.194.17:8080",
        params=params,
    )
    print("*" * 80)
    print("The Answer is: ", res)
