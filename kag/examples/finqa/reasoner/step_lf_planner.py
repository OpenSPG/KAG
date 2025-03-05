import re
import json
import logging
from typing import List, Dict

from tenacity import retry, stop_after_attempt

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import LLMClient, VectorizeModelABC
from kag.interface import PromptABC
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.plan.lf_planner_abc import LFPlannerABC
from kag.interface.solver.base_model import LFPlan, LogicNode
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.parser.logic_node_parser import ParseLogicForm
from kag.solver.logic.core_modules.parser.schema_std import SchemaRetrieval
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.plan.default_lf_planner import DefaultLFPlanner

logger = logging.getLogger()


@LFPlannerABC.register("step_lf_planner")
class StepLFPlanner(DefaultLFPlanner):
    """
    Planner class that extends the base planner functionality to generate sub-queries and logic forms.
    """

    def __init__(
        self,
        logic_form_plan_prompt: PromptABC = None,
        llm_client: LLMClient = None,
        vectorize_model: VectorizeModelABC = None,
        **kwargs,
    ):
        super().__init__(
            llm_client=llm_client,
            logic_form_plan_prompt=logic_form_plan_prompt,
            vectorize_model=vectorize_model,
            **kwargs,
        )

    def _parse_lf(self, question, sub_querys, logic_forms) -> List[LFPlan]:
        if sub_querys is None:
            sub_querys = []
        # process sub query
        sub_querys = [self._process_output_query(question, q) for q in sub_querys]
        parsed_logic_nodes = self.parser.parse_logic_form_set(
            logic_forms, sub_querys, question
        )
        return self._convert_node_to_plan(question, parsed_logic_nodes)

    def _convert_node_to_plan(
        self, question, logic_nodes: List[LogicNode]
    ) -> List[LFPlan]:
        plan_result = []
        for n in logic_nodes:
            lf_type = "retrieval"
            if n.operator == "deduce":
                lf_type = "deduce"
            elif n.operator == "math":
                lf_type = "math"
            elif n.operator == "get":
                lf_type = "output"
            plan_result.append(
                LFPlan(
                    query=n.sub_query,
                    lf_node=n,
                    sub_query_type=lf_type,
                    parent_query=question,
                )
            )
        return plan_result
