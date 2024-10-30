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


class DefaultLFPlanner(LFPlannerABC):
    """
    Planner class that extends the base planner functionality to generate sub-queries and logic forms.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        config = LogicFormConfiguration(kwargs)
        schema = SchemaUtils(config)
        schema.get_schema()
        std_schema = SchemaRetrieval(**kwargs)
        self.parser = ParseLogicForm(schema, std_schema)
        # Load the prompt for generating logic forms based on the business scene and language
        self.logic_form_plan_prompt = PromptOp.load(self.biz_scene, "logic_form_plan")(
            language=self.language
        )

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
        if llm_output is not None:
            sub_querys, logic_forms = self.parse_logic_form_llm_output(llm_output)
        else:
            sub_querys, logic_forms = self.generate_logic_form(question)
        return self._parse_lf(question, sub_querys, logic_forms)

    def _split_sub_query(self, logic_nodes: List[LogicNode]) -> List[LFPlanResult]:
        query_lf_map = {}
        for n in logic_nodes:
            if n.sub_query in query_lf_map.keys():
                query_lf_map[n.sub_query] = query_lf_map[n.sub_query] + [n]
            else:
                query_lf_map[n.sub_query] = [n]
        plan_result = []
        for k, v in query_lf_map.items():
            plan_result.append(LFPlanResult(query=k, lf_nodes=v))
        return plan_result

    def _parse_lf(self, question, sub_querys, logic_forms) -> List[LFPlanResult]:
        if sub_querys is None:
            sub_querys = []
        parsed_logic_nodes = self.parser.parse_logic_form_set(logic_forms, sub_querys, question)
        return self._split_sub_query(parsed_logic_nodes)

    def generate_logic_form(self, question: str):
        return self.llm_module.invoke({'question': question}, self.logic_form_plan_prompt, with_json_parse=False, with_except=True)

    def parse_logic_form_llm_output(self, llm_output):
        _output_string = llm_output.replace("：", ":")
        _output_string = llm_output.strip()
        sub_querys = []
        logic_forms = []
        current_sub_query = ''
        for line in _output_string.split('\n'):
            line = line.strip()
            if line.startswith('Step'):
                sub_querys_regex = re.search('Step\d+:(.*)', line)
                if sub_querys_regex is not None:
                    sub_querys.append(sub_querys_regex.group(1))
                    current_sub_query = sub_querys_regex.group(1)
            elif line.startswith('Output'):
                sub_querys.append("output")
            elif line.startswith('Action'):
                logic_forms_regex = re.search('Action\d+:(.*)', line)
                if logic_forms_regex:
                    logic_forms.append(logic_forms_regex.group(1))
                    if len(logic_forms) - len(sub_querys) == 1:
                        sub_querys.append(current_sub_query)
        return sub_querys, logic_forms
