import re
import logging
from typing import List

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
from kag.solver.plan.default_lf_planner import DefaultLFPlanner
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


@LFPlannerABC.register("law_lf_planner")
class LawLFPlanner(DefaultLFPlanner):
    """
    Planner class that extends the base planner functionality to generate sub-queries and logic forms.
    """

    def __init__(
        self,
        logic_form_plan_prompt: PromptABC = None,
        llm_client: LLMClient = None,
        vectorize_model: VectorizeModelABC = None,
        cot_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__(logic_form_plan_prompt, llm_client, vectorize_model, **kwargs)
        if cot_prompt is None:
            cot_prompt = init_prompt_with_fallback(
                "labor_law_cot_plan", self.biz_scene
            )
        self.cot_prompt = cot_prompt

    @retry(stop=stop_after_attempt(3))
    def get_cot(self, question, state):
        return self.llm_module.invoke({
            'memory': state if state else "",
            'instruction': question
        }, self.cot_prompt, with_json_parse=False, with_except=True)
    def lf_planing(
        self, question: str, memory: KagMemoryABC = None, llm_output=None
    ) -> List[LFPlan]:
        """
        Generates sub-queries and logic forms based on the input question or provided LLM output.

        Parameters:
        question (str): The question or task to plan.
        llm_output (Any, optional): Output from the LLM module. Defaults to None.

        Returns:
        list of LFPlanResult
        """
        state = None
        if memory:
            state = memory.get_solved_answer()

        cot = self.get_cot(question, state)
        instruct = f"{question}\n{cot}"
        return super().lf_planing(instruct, memory)