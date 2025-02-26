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

logger = logging.getLogger()


@LFPlannerABC.register("step_lf_planner")
class StepLFPlanner(LFPlannerABC):
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
        super().__init__(llm_client, **kwargs)
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self.schema.get_schema()
        std_schema = SchemaRetrieval(
            vectorize_model=vectorize_model, llm_client=llm_client, **kwargs
        )
        self.parser = ParseLogicForm(self.schema, std_schema)
        # Load the prompt for generating logic forms based on the business scene and language
        if logic_form_plan_prompt is None:
            logic_form_plan_prompt = init_prompt_with_fallback(
                "finqa_logic_form_plan", self.biz_scene
            )
        self.logic_form_plan_prompt = logic_form_plan_prompt

    # 需要把大模型生成结果记录下来
    def lf_planing(
        self, question: str, memory: KagMemoryABC = None, llm_output=None, **kwargs
    ) -> List[LFPlan]:
        """
        Generates sub-queries and logic forms based on the input question or provided LLM output.

        Parameters:
        question (str): The question or task to plan.
        llm_output (Any, optional): Output from the LLM module. Defaults to None.

        Returns:
        list of LFPlanResult
        """
        sub_querys, logic_forms = self.generate_logic_form(
            question, kwargs.get("process_info", {})
        )
        return self._parse_lf(question, sub_querys, logic_forms)

    def _convert_node_to_plan(self, logic_nodes: List[LogicNode]) -> List[LFPlan]:
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
                LFPlan(query=n.sub_query, lf_node=n, sub_query_type=lf_type)
            )
        return plan_result

    def _process_output_query(self, question, sub_query: str):
        if sub_query is None:
            return question
        if "output" == sub_query.lower():
            return f"output `{question}` answer:"
        return sub_query

    def _parse_lf(self, question, sub_querys, logic_forms) -> List[LFPlan]:
        if sub_querys is None:
            sub_querys = []
        # process sub query
        sub_querys = [self._process_output_query(question, q) for q in sub_querys]
        parsed_logic_nodes = self.parser.parse_logic_form_set(
            logic_forms, sub_querys, question
        )
        return self._convert_node_to_plan(parsed_logic_nodes)

    def generate_logic_form(self, question: str, process_info: Dict = None):
        input_dict = {
            "question": question,
            "context": self.get_context_str(process_info),
        }
        return self.llm_module.invoke(
            input_dict,
            self.logic_form_plan_prompt,
            with_json_parse=True,
            with_except=True,
        )

    def get_context_str(self, process_info: Dict):
        context_list = []
        for i, qa in enumerate(process_info["sub_qa_pair"]):
            a = qa[1]
            lf_plan = process_info["lf_plan"][i]
            context_list.append((lf_plan.query, lf_plan.sub_query_type, a))
        context_str = ""
        for i, c in enumerate(context_list):
            context_str += f"\nSubQuestion{i+1}: {c[0]} by: {c[1]}\nAnswer{i+1}: {c[2]}\n"
        print(context_str)
        return context_str
