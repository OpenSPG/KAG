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

from kag.solver.prompt.default.deduce_choice import DeduceChoice
from kag.solver.prompt.default.deduce_entail import DeduceEntail
from kag.solver.prompt.default.deduce_judge import DeduceJudge
from kag.solver.prompt.default.deduce_multi_choice import DeduceMutiChoice
from kag.solver.prompt.default.logic_form_plan import LogicFormPlanPrompt
from kag.solver.prompt.default.question_ner import QuestionNER
from kag.solver.prompt.default.resp_extractor import RespExtractor
from kag.solver.prompt.default.resp_generator import RespGenerator
from kag.solver.prompt.default.resp_judge import RespJudge
from kag.solver.prompt.default.resp_reflector import RespReflector
from kag.solver.prompt.default.resp_verifier import RespVerifier
from kag.solver.prompt.default.solve_question import SolveQuestion
from kag.solver.prompt.default.solve_question_without_docs import (
    SolveQuestionWithOutDocs,
)
from kag.solver.prompt.default.solve_question_without_spo import SolveQuestionWithOutSPO
from kag.solver.prompt.default.spo_retrieval import SpoRetrieval

__all__ = [
    "DeduceChoice",
    "DeduceEntail",
    "DeduceJudge",
    "DeduceMutiChoice",
    "LogicFormPlanPrompt",
    "QuestionNER",
    "RespExtractor",
    "RespGenerator",
    "RespJudge",
    "RespReflector",
    "RespVerifier",
    "SolveQuestion",
    "SolveQuestionWithOutDocs",
    "SolveQuestionWithOutSPO",
    "SpoRetrieval",
]
