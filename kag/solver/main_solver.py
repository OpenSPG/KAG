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
import logging

from kag.interface import SolverPipelineABC
from kag.tools.info_processor import ReporterIntermediateProcessTool

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.solver.reporter.open_spg_reporter import OpenSPGReporter

logger = logging.getLogger()
math_executor_conf = {
    'type': 'py_code_based_math_executor',
    'llm': '{llm}'
}
kag_hybrid_executor_conf = {
    'type': 'kag_hybrid_executor',
    'lf_rewriter': {
        'llm_client': '{llm}',
        'lf_trans_prompt': {'type': 'default_spo_retriever_decompose'},
        'vectorize_model': '{vectorize_model}',
        'type': 'kag_spo_lf'
    },
    'flow': 'kg_cs->kg_fr->rc\n'
}
executors = []
default_pipeline_template = {
    'generator': {
        'llm_client': '{llm}',
        'type': 'llm_generator',
        'generated_prompt': {'type': 'default_refer_generator_prompt'}
    },
    'type': 'kag_iterative_pipeline',
    'planner': {
        'plan_prompt': {'type': 'default_thought_iterative_planning'},
        'type': 'kag_iterative_planner',
        'llm': '{llm}'
    }
}

def replace_placeholders(config, replacements):
    """
    替换配置字典中花括号 {} 中的变量。

    :param config: 需要替换的配置字典
    :param replacements: 一个字典，键是占位符名称，值是要替换的内容
    :return: 替换后的配置字典
    """
    if isinstance(config, dict):
        return {key: replace_placeholders(value, replacements) for key, value in config.items()}
    elif isinstance(config, list):
        return [replace_placeholders(item, replacements) for item in config]
    elif isinstance(config, str):
        if config.startswith("{") and config.endswith("}"):
            placeholder = config[1:-1]  # 去掉花括号
            if placeholder in replacements:
                return replacements[placeholder]
        return config
    else:
        return config

async def qa(task_id, query, project_id, host_addr):
    # resp
    reporter: OpenSPGReporter = OpenSPGReporter(
        task_id=task_id, host_addr=host_addr, project_id=project_id
    )
    await reporter.start()
    try:
        llm = KAG_CONFIG.all_config.get("llm", None)
        if llm is None:
            raise Exception("llm config is not set")
        llm['stream'] = True
        vectorize_model = KAG_CONFIG.all_config.get("vectorize_model", None)
        if vectorize_model is None:
            raise Exception("vectorize_model config is not set")
        default_conf = dict(default_pipeline_template)
        default_conf["executors"] = [
            math_executor_conf,
            kag_hybrid_executor_conf
        ]
        placeholder_config = {
            "llm": llm,
            "vectorize_model": vectorize_model
        }
        default_pipeline = replace_placeholders(default_conf, placeholder_config)

        conf = copy.deepcopy(KAG_CONFIG.all_config.get("kag_solver_pipeline", default_pipeline))
        pipeline = SolverPipelineABC.from_config(conf)

        answer = await pipeline.ainvoke(query, reporter=reporter)
    except Exception as e:
        answer = None
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
    ):
        answer = None
        try:
            answer = asyncio.run(qa(task_id=task_id, project_id=project_id, host_addr=host_addr, query=query))
            logger.info(f"{query} answer={answer}")
        except Exception as e:
            logger.warning(
                f"An exception occurred while processing query: {query}. Error: {str(e)}",
                exc_info=True,
            )
        return answer


if __name__ == "__main__":
    from kag.bridge.spg_server_bridge import init_kag_config

    init_kag_config(
        "4000003", "http://127.0.0.1:8887"
    )
    res = SolverMain().invoke(
        4000003,
        5600004,
        "随机生成两个100000到200000之间的素数，计算他们的乘积",
        "3500005",
        True,
        host_addr="http://127.0.0.1:8887",
    )
    print("*" * 80)
    print("The Answer is: ", res)
