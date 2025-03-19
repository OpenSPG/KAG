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

from knext.project.client import ProjectClient

from kag.solver.common.base import Question
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag_ant.medicine_thinker.med_thinker import MedicineThinker
from kag_ant.thinker.thinker import Thinker


class SolverMain:

    def invoke_backup(
        self,
        project_id: int,
        task_id: int,
        query: str,
        report_tool=True,
        session_id: int = 0,
        host_addr="http://127.0.0.1:8887",
    ):
        # resp
        report_tool = ReporterIntermediateProcessTool(
            report_log=report_tool,
            task_id=task_id,
            project_id=project_id,
            host_addr=host_addr,
        )

        lf_planner = DefaultLFPlanner(
            KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr
        )
        lf_solver = LFSolver(
            kg_retriever=KGRetrieverByLlm(
                KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr
            ),
            chunk_retriever=LFChunkRetriever(
                KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr
            ),
            report_tool=report_tool,
            KAG_PROJECT_ID=project_id,
            KAG_PROJECT_HOST_ADDR=host_addr,
        )
        reason = DefaultReasoner(
            lf_planner=lf_planner,
            lf_solver=lf_solver,
            KAG_PROJECT_ID=project_id,
            KAG_PROJECT_HOST_ADDR=host_addr,
        )
        question = Question(query)
        question.id = 0
        resp = SolverPipeline(
            reasoner=reason, KAG_PROJECT_ID=project_id, KAG_PROJECT_HOST_ADDR=host_addr
        )
        answer, trace_log = resp.run(query)
        print(trace_log)
        report_tool.report_node(
            question, answer, ReporterIntermediateProcessTool.STATE.FINISH
        )
        return answer

    def invoke(
        self,
        project_id: int,
        task_id: int,
        query: str,
        report_tool=True,
        session_id: int = 0,
        host_addr="http://127.0.0.1:8887",
    ):
        from kag.examples.finstate.solver.solver import FinStateSolver

        report_tool = ReporterIntermediateProcessTool(
            report_log=report_tool,
            task_id=task_id,
            project_id=project_id,
            host_addr=host_addr,
        )
        solver = FinStateSolver(
            report_tool=report_tool, KAG_PROJECT_ID=project_id, session_id=session_id
        )
        answer = solver.run(query)
        return answer

    def invoke_med_thinker(
        self,
        project_id: int,
        task_id: int,
        query: str,
        report_tool=True,
        session_id: int = 0,
        host_addr="http://127.0.0.1:8887",
    ):
        # resp
        report_tool = ReporterIntermediateProcessTool(
            report_log=report_tool,
            task_id=task_id,
            project_id=project_id,
            host_addr=host_addr,
        )
        thinker = MedicineThinker(report_tool=report_tool)
        resp = thinker.diagnostic_evidence(query)
        return resp

    def invoke_folio(
        self,
        project_id: int,
        task_id: int,
        query: str,
        report_tool=True,
        session_id: int = 0,
        host_addr="http://127.0.0.1:8887",
    ):
        # resp
        report_tool = ReporterIntermediateProcessTool(
            report_log=report_tool,
            task_id=task_id,
            project_id=project_id,
            host_addr=host_addr,
        )
        config = ProjectClient(host_addr=host_addr, project_id=project_id).get_config(
            project_id
        )
        llm_config = eval(os.getenv("KAG_LLM", "{}"))
        llm_config.update(config.get("llm", {}))
        thinker = Thinker(env="dev", report_tool=report_tool, llm_config=llm_config)
        response = thinker.run_folio(question=query)
        return response["thinkerCot"]


if __name__ == "__main__":
    res = SolverMain().invoke(
        3,
        283,
        "周杰伦在哪一年基于什么作品获得的全球畅销专辑榜”冠军的华语歌手",
        True,
        host_addr="http://127.0.0.1:8887",
    )
    print("*" * 80)
    print("The Answer is: ", res)
