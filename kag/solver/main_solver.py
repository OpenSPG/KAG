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

from kag.common.conf import KAG_CONFIG,KAG_PROJECT_CONF


class SolverMain:
    def invoke(
            self,
            project_id: int,
            task_id: int,
            query: str,
            is_report=True,
            host_addr="http://127.0.0.1:8887",
    ):
        # resp
        report_tool = ReporterIntermediateProcessTool(
            report_log=is_report,
            task_id=str(task_id),
            project_id=str(project_id),
            host_addr=host_addr,
            language=KAG_PROJECT_CONF.language
        )
        default_pipeline_config = {
            'generator': {
                'generate_prompt': {
                    'type': 'default_resp_generator'
                }
            },
            'reasoner': {
                'lf_planner': {
                    'type': 'base'
                },
                'lf_executor': {
                    'chunk_retriever': {
                        'recall_num': 10,
                        'rerank_topk': 10,
                        'type': 'default_chunk_retriever'
                    },
                    'exact_kg_retriever': {
                        'el_num': 5,
                        'graph_api': {
                            'type': 'openspg'
                        },
                        'search_api': {
                            'type': 'openspg'
                        },
                        'type': 'default_exact_kg_retriever'
                    },
                    'force_chunk_retriever': True,
                    'fuzzy_kg_retriever': {
                        'el_num': 5,
                        'graph_api': {
                            'type': 'openspg'
                        },
                        'search_api': {
                            'type': 'openspg'
                        },
                        'type': 'default_fuzzy_kg_retriever',
                    },
                    'merger': {
                        'chunk_retriever': {
                            'recall_num': 10,
                            'rerank_topk': 10,
                            'type': 'default_chunk_retriever',
                        },
                        'type': 'base'
                    },
                    'type': 'base'
                },
                'type': 'base'
            }
        }
        conf = copy.deepcopy(KAG_CONFIG.all_config.get("lf_solver_pipeline", default_pipeline_config))
        resp = SolverPipeline.from_config(conf)
        answer, trace_log = resp.run(query, report_tool=report_tool)
        print(trace_log)
        report_tool.report_final_answer(
            query, answer, ReporterIntermediateProcessTool.STATE.FINISH
        )
        return answer


if __name__ == "__main__":
    res = SolverMain().invoke(
        300027,
        2800106,
        "who is Jay Zhou",
        True
    )
    print("*" * 80)
    print("The Answer is: ", res)
