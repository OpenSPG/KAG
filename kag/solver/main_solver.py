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

    def invoke(self, project_id: int, task_id: int, query: str, report_tool=True):
        # resp
        report_tool = ReporterIntermediateProcessTool(report_log=report_tool, task_id=task_id, project_id=project_id)

        lf_planner = DefaultLFPlanner(KAG_PROJECT_ID=project_id)
        lf_solver = LFSolver(
            kg_retriever=KGRetrieverByLlm(KAG_PROJECT_ID=project_id),
            chunk_retriever=LFChunkRetriever(project_id=project_id),
            report_tool=report_tool,
            KAG_PROJECT_ID=project_id
        )
        reason = DefaultReasoner(lf_planner=lf_planner, lf_solver=lf_solver)
        question = Question(query)
        question.id = 0
        resp = SolverPipeline(reasoner=reason)
        answer, trace_log = resp.run(query)
        report_tool.report_node(question, answer, ReporterIntermediateProcessTool.STATE.FINISH)
        return answer

if __name__ == "__main__":
    res = SolverMain().invoke("10", None, "在哪一年周杰伦凭借什么专辑获得第22届台湾金曲奖的？", False)
    print("*" * 80)
    print("The Answer is: ", res)
