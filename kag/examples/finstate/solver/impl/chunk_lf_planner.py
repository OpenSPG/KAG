import os
import re
from typing import List

from kag.common.base.prompt_op import PromptOp
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.logic.core_modules.common.base_model import LFPlanResult, LogicNode
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.parser.logic_node_parser import ParseLogicForm
from kag.solver.logic.core_modules.retriver.schema_std import SchemaRetrieval


class ChunkLFPlanner(LFPlannerABC):
    """
    Planner class that extends the base planner functionality to generate sub-queries and logic forms.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # 需要把大模型生成结果记录下来
    def lf_planing(self, question, llm_output=None) -> List[LFPlanResult]:
        """
        Generates sub-queries and logic forms based on the input question or provided LLM output.

        Parameters:
        question (str): The question or task to plan.
        llm_output (Any, optional): Output from the LLM module. Defaults to None.

        Returns:
        list of LFPlanResult
        """
        return []