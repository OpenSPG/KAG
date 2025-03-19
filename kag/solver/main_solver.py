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
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.solver_new.reporter.open_spg_reporter import OpenSPGReporter

logger = logging.getLogger()


async def qa(reporter, pipeline, query):
    await reporter.start()
    try:
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

        # resp
        reporter: OpenSPGReporter = OpenSPGReporter(task_id=task_id, host_addr=host_addr, project_id=project_id)

        conf = copy.deepcopy(
            KAG_CONFIG.all_config.get("kag_solver_pipeline", None)
        )
        resp = SolverPipelineABC.from_config(conf)
        try:

            answer = asyncio.run(qa(reporter=reporter, pipeline=resp, query=query))
            logger.info(f"{query} answer={answer}")
        except Exception as e:
            if KAG_PROJECT_CONF.language == "en":
                answer = f"Sorry, An exception occurred while processing query: {query}. Error: {str(e)}, please retry."
            else:
                answer = f"抱歉，处理查询 {query} 时发生异常。错误：{str(e)}, 请重试。"

            state = ReporterIntermediateProcessTool.STATE.ERROR
            logger.warning(
                f"An exception occurred while processing query: {query}. Error: {str(e)}",
                exc_info=True,
            )
        return answer


if __name__ == "__main__":
    from kag.bridge.spg_server_bridge import init_kag_config

    init_kag_config(
        "4000003", "http://antspg-gz00b-006002021225.sa128-sqa.alipay.net:8887"
    )
    res = SolverMain().invoke(4000003, 5000007, "周润发的少年经历介绍下", "3500005", True, host_addr="http://antspg-gz00b-006002021225.sa128-sqa.alipay.net:8887")
    print("*" * 80)
    print("The Answer is: ", res)
