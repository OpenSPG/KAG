from typing import Union

from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.op_executor.op_executor import OpExecutor
from kag.solver.logic.parser.logic_node_parser import CountNode, SumNode


class MathExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: Schema, debug_info: dict):
        super().__init__(nl_query, kg_graph, schema, debug_info)

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, (CountNode, SumNode))

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        pass
