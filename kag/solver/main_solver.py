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
import copy
import os

from kag.common.registry import import_modules_from_path
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF


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
        report_tool = ReporterIntermediateProcessTool(
            report_log=is_report,
            task_id=str(task_id),
            project_id=str(project_id),
            host_addr=host_addr,
            language=KAG_PROJECT_CONF.language,
        )
        llm_client = KAG_CONFIG.all_config["llm"]
        default_pipeline_config = {
            "max_iterations": 3,
            "memory": {"type": "default_memory", "llm_client": llm_client},
            "generator": {
                "generate_prompt": {"type": "default_resp_generator"},
                "llm_client": llm_client,
                "type": "default_generator",
            },
            "reasoner": {
                "lf_executor": {
                    "chunk_retriever": {
                        "recall_num": 10,
                        "rerank_topk": 10,
                        "type": "default_chunk_retriever",
                        "llm_client": llm_client,
                    },
                    "exact_kg_retriever": {
                        "el_num": 5,
                        "graph_api": {"type": "openspg_graph_api"},
                        "search_api": {"type": "openspg_search_api"},
                        "type": "default_exact_kg_retriever",
                        "llm_client": llm_client,
                    },
                    "force_chunk_retriever": True,
                    "fuzzy_kg_retriever": {
                        "el_num": 5,
                        "graph_api": {"type": "openspg_graph_api"},
                        "search_api": {"type": "openspg_search_api"},
                        "type": "default_fuzzy_kg_retriever",
                        "llm_client": llm_client,
                    },
                    "merger": {
                        "chunk_retriever": {
                            "recall_num": 10,
                            "rerank_topk": 10,
                            "llm_client": llm_client,
                            "type": "default_chunk_retriever",
                        },
                        "type": "default_lf_sub_query_res_merger",
                    },
                    "llm_client": llm_client,
                    "type": "default_lf_executor",
                },
                "lf_planner": {
                    "type": "default_lf_planner",
                    "llm_client": llm_client,
                },
                "llm_client": llm_client,
                "type": "default_reasoner",
            },
            "reflector": {"type": "default_reflector", "llm_client": llm_client},
        }
        conf = copy.deepcopy(
            KAG_CONFIG.all_config.get("kag_solver_pipeline", default_pipeline_config)
        )
        resp = SolverPipeline.from_config(conf)
        answer, trace_log = resp.run(query, report_tool=report_tool, session_id=session_id)
        print(trace_log)
        report_tool.report_final_answer(
            query, answer, ReporterIntermediateProcessTool.STATE.FINISH
        )
        return answer


if __name__ == "__main__":
    from kag.bridge.spg_server_bridge import init_kag_config

    init_kag_config("2", "http://127.0.0.1:8887")
    res = SolverMain().invoke(2, 19, "我上班的时候受伤了，能认定工伤吗？", "6", True)
    print("*" * 80)
    print("The Answer is: ", res)
