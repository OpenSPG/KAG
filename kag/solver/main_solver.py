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

from kag.common.llm.client import LLMClient
from kag.solver.common.base import Question
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool


class SolverMain:

    def invoke(self, project_id: int, task_id: int, query: str, report_tool=True, host_addr="http://127.0.0.1:8887"):
        # resp
        report_tool = ReporterIntermediateProcessTool(report_log=report_tool, task_id=task_id, project_id=project_id, host_addr=host_addr)

        lf_planner = DefaultLFPlanner(KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr)
        lf_solver = LFSolver(
            kg_retriever=KGRetrieverByLlm(KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr),
            chunk_retriever=LFChunkRetriever(KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr),
            report_tool=report_tool,
            KAG_PROJECT_ID=project_id,
            KAG_PROJECT_HOST_ADDR=host_addr
        )
        reason = DefaultReasoner(lf_planner=lf_planner, lf_solver=lf_solver, KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr)
        question = Question(query)
        question.id = 0
        resp = SolverPipeline(reasoner=reason, KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr)
        answer, trace_log = resp.run(query)
        print(trace_log)
        report_tool.report_node(question, answer, ReporterIntermediateProcessTool.STATE.FINISH)
        return answer


if __name__ == "__main__":
    res = SolverMain().invoke(3, 283, "周杰伦在哪一年基于什么作品获得的全球畅销专辑榜”冠军的华语歌手", True, host_addr="http://127.0.0.1:8887")
    print("*" * 80)
    print("The Answer is: ", res)
