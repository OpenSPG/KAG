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
import copy
import json
import logging
import os
import re

import yaml
from kag.common.conf import KAGConfigMgr, KAGConfigAccessor, KAGConstants
from kag.indexer import KAGIndexManager
from kag.interface import SolverPipelineABC
from knext.project.client import ProjectClient
from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.interface.solver.reporter_abc import ReporterABC

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
                f"Placeholder '{placeholder}' '{'or ' + backup_key if backup_key else ''}' not found in config."
            )
        if "llm" in placeholder or "vectorizer" in placeholder:
            value["enable_check"] = False
        placeholders_replacement_map[placeholder] = value
    default_pipeline_conf = replace_placeholders(
        conf_map[use_pipeline_name], placeholders_replacement_map
    )
    default_solver_pipeline = default_pipeline_conf[pipeline_name]

    if use_pipeline_name == "mcp_pipeline":
        mcp_servers = config["kb"][0]["mcp_servers"]
        logger.info(f"mcp_servers = {mcp_servers}")
        logger.info(f"config = {config}")
        mcp_executors = []
        if mcp_servers is not None:
            for mcp_name, mcp_conf in mcp_servers.items():
                desc = mcp_conf.get("description", "")
                env = mcp_conf.get("env", {})
                store_path = mcp_conf.get("store_path", "")
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

    return default_solver_pipeline


def is_chinese(text):
    chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
    return bool(chinese_pattern.search(text))


async def do_qa_pipeline(
    use_pipeline, query, qa_config, reporter, task_id, kb_project_ids
):
    retriever_configs = []
    kb_configs = qa_config.get("kb", [])
    for kb_project_id in kb_project_ids:
        kb_task_project_id = f"{task_id}_{kb_project_id}"
        try:
            kag_config = KAGConfigAccessor.get_config(kb_task_project_id)
            matched_kb = next(
                (kb for kb in kb_configs if kb.get("id") == kb_project_id), None
            )
            if not matched_kb:
                reporter.warning(
                    f"Knowledge base with id {kb_project_id} not found in qa_config['kb']"
                )
                continue
            index_list = matched_kb.get("index_list", [])
            if use_pipeline in ["default_pipeline"]:
                # we only use chunk index
                index_list = ["chunk_index"]
            for index_name in index_list:
                index_manager = KAGIndexManager.from_config(
                    {
                        "type": index_name,
                        "llm_config": qa_config.get("llm", {}),
                        "vectorize_model_config": kag_config.all_config.get(
                            "vectorize_model", {}
                        ),
                    }
                )
                retriever_configs.extend(
                    index_manager.build_retriever_config(
                        qa_config.get("llm", {}),
                        kag_config.all_config.get("vectorize_model", {}),
                        kag_qa_task_config_key=kb_task_project_id,
                    )
                )
        except Exception as e:
            logger.error(f"Error processing kb_project_id {kb_project_id}: {str(e)}")
            continue
    qa_config["retrievers"] = retriever_configs

    if use_pipeline in qa_config.keys():
        custom_pipeline_conf = copy.deepcopy(qa_config.get(use_pipeline, None))
    else:
        custom_pipeline_conf = copy.deepcopy(qa_config.get("solver_pipeline", None))
    if use_pipeline not in ["index_pipeline"]:
        self_cognition_conf = get_pipeline_conf("self_cognition_pipeline", qa_config)
        self_cognition_pipeline = SolverPipelineABC.from_config(self_cognition_conf)
        self_cognition_res = await self_cognition_pipeline.ainvoke(
            query, reporter=reporter
        )
    else:
        self_cognition_res = False
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
    return answer


async def qa(task_id, query, project_id, host_addr, app_id, params={}):
    main_config = params.get("config", KAGConfigAccessor.get_config().all_config)
    if isinstance(main_config, str):
        main_config = json.loads(main_config)

    KAG_PROJECT_CONF.host_addr = host_addr
    KAG_PROJECT_CONF.language = "zh" if is_chinese(query) else "en"

    use_pipeline = (
        main_config["chat"]["ename"]
        if isinstance(main_config.get("chat"), dict)
        else params.get("usePipeline", "think_pipeline")
    )

    # process llm
    if "extra_body" in main_config["llm"] and main_config["llm"]["type"] in [
        "openai",
        "ant_openai",
        "maas",
        "vllm",
    ]:
        extra_body = main_config["llm"]["extra_body"]
        if isinstance(extra_body, str):
            try:
                extra_body_json = json.loads(extra_body)
            except:
                extra_body_json = {}
            main_config["llm"]["extra_body"] = extra_body_json

    kb_configs = {}
    kb_project_ids = []
    vectorize_model = {}
    global_index_set = main_config.get("chat", {}).get("index_list", [])
    if isinstance(main_config.get("kb"), list):
        kbs = main_config["kb"]
        for kb in kbs:
            try:
                kb_project_id = kb.get("id") or kb.get("project", {}).get("id")
                if not kb_project_id:
                    continue

                kb_project_ids.append(kb_project_id)
                kb_task_project_id = f"{task_id}_{kb_project_id}"

                kb_conf = KAGConfigMgr()
                kb_conf.update_conf(kb)

                global_config = kb.get(KAGConstants.PROJECT_CONFIG_KEY, {})
                kb_conf.global_config.initialize(**global_config)
                project_client = ProjectClient(
                    host_addr=host_addr, project_id=kb_project_id
                )
                project = project_client.get_by_id(kb_project_id)

                kb_conf.global_config.project_id = kb_project_id
                kb_conf.global_config.namespace = project.namespace
                kb_conf.global_config.host_addr = host_addr
                kb_conf.global_config.language = KAG_PROJECT_CONF.language

                if "llm" in main_config:
                    kb_conf.update_conf({"llm": main_config["llm"]})
                if "vectorizer" in kb:
                    kb_conf.update_conf({"vectorize_model": kb["vectorizer"]})
                    vectorize_model = kb["vectorizer"]
                if "index_list" not in kb and global_index_set:
                    kb["index_list"] = global_index_set
                KAGConfigAccessor.set_task_config(kb_task_project_id, kb_conf)
                kb_configs[kb_project_id] = (kb_task_project_id, kb_conf)
            except Exception as e:
                logger.error(f"KB配置初始化失败: {str(e)}", exc_info=True)
    if "vectorize_model" not in main_config.keys():
        main_config["vectorize_model"] = vectorize_model

    if vectorize_model:
        KAG_CONFIG.update_conf({"vectorize_model": vectorize_model})
    if main_config["llm"]:
        KAG_CONFIG.update_conf({"llm": main_config["llm"]})
    reporter_map = {"kag_thinker_pipeline": "kag_open_spg_reporter"}

    reporter_config = {
        "type": reporter_map.get(use_pipeline, "open_spg_reporter"),
        "task_id": task_id,
        "host_addr": host_addr,
        "project_id": project_id,
        "thinking_enabled": use_pipeline
        in ["think_pipeline", "index_pipeline", "kag_thinker_pipeline"],
        "report_all_references": use_pipeline == "index_pipeline",
    }
    reporter = ReporterABC.from_config(reporter_config)

    try:
        await reporter.start()
        answer = await do_qa_pipeline(
            use_pipeline,
            query,
            main_config,
            reporter,
            task_id=task_id,
            kb_project_ids=kb_project_ids,
        )
        reporter.add_report_line("answer", "Final Answer", answer, "FINISH")

    except Exception as e:
        logger.warning(
            f"An exception occurred while processing query: {query}. Error: {str(e)}",
            exc_info=True,
        )

        if is_chinese(query):
            answer = f"抱歉，处理查询 {query} 时发生异常。错误：{str(e)}, 请重试。"
        else:
            answer = f"Sorry, An exception occurred while processing query: {query}. Error: {str(e)}, please retry."
        reporter.add_report_line("answer", "Final Answer", answer, "ERROR")

    finally:
        await reporter.stop()

    return answer


class SolverMain:
    def invoke(
        self,
        project_id: int,
        task_id,
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

    async def ainvoke(
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
            answer = await qa(
                task_id=task_id,
                project_id=project_id,
                host_addr=host_addr,
                query=query,
                params=params,
                app_id=app_id,
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
    # init_kag_config(
    #     "4200052", "https://spg-pre.alipay.com"
    # )
    config = {}
    params = {"config": config}
    res = SolverMain().invoke(
        2100007,
        11200009,
        # "阿里巴巴2024年截止到9月30日的总收入是多少元？ 如果把这笔钱于当年10月3日存入银行并于12月29日取出，银行日利息是万分之0.9，本息共可取出多少元？",
        "营业执照不通过",
        "9500005",
        True,
        host_addr="http://spg-pre.alipay.com",
        # host_addr="http://antspg-gz00b-006001164035.sa128-sqa.alipay.net:8887",
        params=params,
    )
    print("*" * 80)
    print("The Answer is: ", res)
