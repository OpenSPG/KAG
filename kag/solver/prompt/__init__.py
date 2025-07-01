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
import kag.solver.prompt.kag_model
from kag.solver.prompt.context_select_prompt import ContextSelectPrompt
from kag.solver.prompt.deduce_choice import DeduceChoice
from kag.solver.prompt.deduce_entail import DeduceEntail
from kag.solver.prompt.deduce_extractor import DeduceExtractor
from kag.solver.prompt.deduce_judge import DeduceJudge
from kag.solver.prompt.deduce_multi_choice import DeduceMutiChoice
from kag.solver.prompt.expression_builder import ExpressionBuildr
from kag.solver.prompt.lf_static_planning_prompt import RetrieverLFStaticPlanningPrompt
from kag.solver.prompt.logic_form_plan import LogicFormPlanPrompt
from kag.solver.prompt.multi_hop_generator import MultiHopGeneratorPrompt
from kag.solver.prompt.question_ner import QuestionNER
from kag.solver.prompt.resp_extractor import RespExtractor
from kag.solver.prompt.resp_generator import RespGenerator
from kag.solver.prompt.resp_judge import RespJudge
from kag.solver.prompt.resp_reflector import RespReflector
from kag.solver.prompt.resp_verifier import RespVerifier
from kag.solver.prompt.rewrite_sub_query import DefaultRewriteSubQuery
from kag.solver.prompt.solve_question import SolveQuestion

from kag.solver.prompt.solve_question_without_docs import (
    SolveQuestionWithOutDocs,
)
from kag.solver.prompt.solve_question_without_spo import SolveQuestionWithOutSPO
from kag.solver.prompt.spo_retrieval import SpoRetrieval
from kag.solver.prompt.query_rewrite_prompt import QueryRewritePrompt
from kag.solver.prompt.reference_generator import ReferGeneratorPrompt
from kag.solver.prompt.retriever_static_planning_prompt import (
    RetrieverStaticPlanningPrompt,
)
from kag.solver.prompt.spo_retriever_decompose_prompt import (
    DefaultSPORetrieverDecomposePrompt,
)
from kag.solver.prompt.static_planning_prompt import DefaultStaticPlanningPrompt
from kag.solver.prompt.thought_iterative_planning_prompt import (
    DefaultIterativePlanningPrompt,
)
from kag.solver.prompt.sub_question_summary import SubQuestionSummary
from kag.solver.prompt.summary_question import SummaryQuestionWithOutSPO
from kag.solver.prompt.mcp_tool_call import MCPToolCallPrompt
from kag.solver.prompt.thought_then_answer import ThoughtThenAnswerPrompt
from kag.solver.prompt.without_reference_generator import WithOutReferGeneratorPrompt
from kag.solver.prompt.atomic_query_rewrite_prompt import AtomicQueryRewritePrompt

__all__ = [
    "DeduceChoice",
    "DeduceExtractor",
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
    "ExpressionBuildr",
    "DefaultRewriteSubQuery",
    "QueryRewritePrompt",
    "ReferGeneratorPrompt",
    "RetrieverStaticPlanningPrompt",
    "DefaultSPORetrieverDecomposePrompt",
    "DefaultStaticPlanningPrompt",
    "DefaultIterativePlanningPrompt",
    "SubQuestionSummary",
    "SummaryQuestionWithOutSPO",
    "RetrieverLFStaticPlanningPrompt",
    "MCPToolCallPrompt",
    "WithOutReferGeneratorPrompt",
    "ThoughtThenAnswerPrompt",
    "MultiHopGeneratorPrompt",
    "AtomicQueryRewritePrompt",
    "ContextSelectPrompt",
]
