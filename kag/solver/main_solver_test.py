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

from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF


class SolverMain:
    def invoke(
        self,
        project_id: int,
        task_id: int,
        query: str,
        is_report=True,
    ):
        KAG_CONFIG.config["llm"] = {
            "api_key": "sk-4323e7aaab36449fab52b0ed86e29696",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "type": "maas",
        }
        host_addr = KAG_PROJECT_CONF.host_addr
        # resp
        report_tool = ReporterIntermediateProcessTool(
            report_log=is_report,
            task_id=str(task_id),
            project_id=str(project_id),
            host_addr=host_addr,
        )
        default_vectorize = {
            "api_key": "sk-yndixxjfxvnsqfkvfuyubkxidhtwicjcflprvqguffrmxbrv",
            "base_url": "https://api.siliconflow.cn/v1/",
            "model": "netease-youdao/bce-embedding-base_v1",
            "type": "openai",
            "vector_dimensions": 768,
        }
        KAG_CONFIG.config["vectorize_model"] = default_vectorize
        default_pipeline_config = {
            "max_iterations": 3,
            "memory": "default_memory",
            "generator": {
                "generate_prompt": {"type": "default_resp_generator"},
                "type": "default_generator",
            },
            "reasoner": {
                "lf_executor": {
                    "chunk_retriever": {
                        "recall_num": 10,
                        "rerank_topk": 10,
                        "type": "default_chunk_retriever",
                    },
                    "exact_kg_retriever": {
                        "el_num": 5,
                        "graph_api": {"type": "openspg_graph_api"},
                        "search_api": {"type": "openspg_search_api"},
                        "type": "default_exact_kg_retriever",
                    },
                    "force_chunk_retriever": True,
                    "fuzzy_kg_retriever": {
                        "el_num": 5,
                        "graph_api": {"type": "openspg_graph_api"},
                        "search_api": {"type": "openspg_search_api"},
                        "type": "default_fuzzy_kg_retriever",
                        "vectorize_model": default_vectorize,
                    },
                    "merger": {
                        "chunk_retriever": {
                            "recall_num": 10,
                            "rerank_topk": 10,
                            "type": "default_chunk_retriever",
                        },
                        "type": "default_lf_sub_query_res_merger",
                    },
                    "type": "default_lf_executor",
                },
                "lf_planner": {"type": "default_lf_planner"},
                "type": "default_reasoner",
            },
            "reflector": {"type": "default_reflector"},
        }
        conf = copy.deepcopy(
            KAG_CONFIG.all_config.get("lf_solver_pipeline", default_pipeline_config)
        )
        resp = SolverPipeline.from_config(conf)
        answer, trace_log = resp.run(query, report_tool=report_tool)
        print(trace_log)
        report_tool.report_final_answer(
            query, answer, ReporterIntermediateProcessTool.STATE.FINISH
        )
        return answer


if __name__ == "__main__":
    res = SolverMain().invoke(300027, 2800106, "who is Jay Zhou", True)
    print("*" * 80)
    print("The Answer is: ", res)
