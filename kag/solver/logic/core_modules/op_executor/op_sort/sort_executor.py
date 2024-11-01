from typing import Union

from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import SortNode


class SortExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, debug_info: dict, **kwargs):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, SortNode)
    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        pass
