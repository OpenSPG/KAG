from typing import Union

from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.op_executor.op_math.sympy_math.sympy_math_op import SymPyMathOp
from kag.solver.logic.core_modules.op_executor.op_math.sympy_math.llm_math_op import LLMPyMathOp
from kag.solver.logic.core_modules.parser.logic_node_parser import CountNode, SumNode, MathNode


class MathExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, debug_info: dict, **kwargs):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)

        self.op_mapping = {
            #'math': SymPyMathOp(self.nl_query, self.kg_graph, self.schema, self.debug_info, **kwargs),
            'math': LLMPyMathOp(self.nl_query, self.kg_graph, self.schema, self.debug_info, **kwargs)
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, (CountNode, SumNode, MathNode))

    def executor(self, logic_node: LogicNode, history:dict, init_query:str,req_id: str, param: dict) -> Union[KgGraph, list]:
        if isinstance(logic_node, MathNode):
            return self.op_mapping['math'].executor(logic_node, history, init_query, req_id, param)
        raise NotImplementedError(f"{logic_node}")
