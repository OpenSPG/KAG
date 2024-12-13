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

from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag_ant.thinker.thinker import Thinker


class SolverMain:

    def invoke(self, project_id: int, task_id: int, query: str, report_tool=True, host_addr="http://127.0.0.1:8887"):
        # resp
        report_tool = ReporterIntermediateProcessTool(report_log=report_tool, task_id=task_id, project_id=project_id, host_addr=host_addr)
        config = ProjectClient(host_addr=host_addr, project_id=project_id).get_config(project_id)

        llm_config = eval(os.getenv("KAG_LLM", "{}"))
        llm_config.update(config.get("llm", {}))
        thinker = Thinker(env="dev", report_tool=report_tool, llm_config=llm_config)
        response = thinker.run_folio(question=query)
        report_tool.report_markdown(response['thinkerCot'])
        return response['thinkerCot']


if __name__ == "__main__":
    context="All people who regularly drink coffee are dependent on caffeine. People either regularly drink coffee or joke about being addicted to caffeine. No one who jokes about being addicted to caffeine is unaware that caffeine is a drug. Rina is either a student and unaware that caffeine is a drug, or neither a student nor unaware that caffeine is a drug. If Rina is not a person dependent on caffeine and a student, then Rina is either a person dependent on caffeine and a student, or neither a person dependent on caffeine nor a student."
    question="Based on the above information, is the following statement true, false, or uncertain? Rina is either a person who jokes about being addicted to caffeine or is unaware that caffeine is a drug."
    query = {'context': context, 'question': question}
    res = SolverMain().invoke(1500002, 900001, json.dumps(query), True, host_addr="http://127.0.0.1:8887")
    print("*" * 80)
    print("The Answer is: ", res)
