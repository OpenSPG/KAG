import json
from sympy import FiniteSet
from sympy.core.sympify import SympifyError

from kag.common.llm.client import LLMClient
from kag.common.base.prompt_op import PromptOp
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import MathNode


class LLMPyMathOp(OpExecutor):
    def __init__(
        self,
        nl_query: str,
        kg_graph: KgGraph,
        schema: SchemaUtils,
        debug_info: dict,
        **kwargs
    ):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)
        self.expression_builder = PromptOp.load(self.biz_scene, "expression_builder")(
            language=self.language, project_id=self.project_id
        )

    def executor(
        self,
        logic_node: MathNode,
        history: list,
        init_query: str,
        req_id: str,
        param: dict,
    ) -> list:
        llm: LLMClient = self.llm_module
        input_str = self._get_input(
            logic_node=logic_node, history=history, init_query=init_query
        )
        expression = llm.invoke({"input": input_str}, self.expression_builder)
        if "i don't know" in expression.lower():
            return "I don't know"
        try:
            rst = eval(str(expression))
        except SympifyError:
            pass
        return [f"{logic_node.alias_name}={rst}"]

    def _get_input(self, logic_node: MathNode, history: list, init_query: str):
        input_dict = {}
        input_dict["question"] = logic_node.sub_query
        input_dict["context"] = {}
        input_dict["context"]["overall_question"] = init_query
        input_dict["context"]["history"] = [
            {k: h[k] for k in {"sub_query", "sub_answer"}} for h in history
        ]
        return json.dumps(input_dict, indent=2, ensure_ascii=False)
