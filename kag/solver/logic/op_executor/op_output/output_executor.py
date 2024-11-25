from typing import Union

from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.op_executor.op_executor import OpExecutor
from kag.solver.logic.op_executor.op_output.module.get_executor import GetExecutor
from kag.solver.logic.parser.logic_node_parser import GetNode
from kag.solver.logic.retriver.entity_linker import EntityLinkerBase
from kag.solver.logic.retriver.graph_retriver.dsl_executor import DslRunner


class OutputExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: Schema, el: EntityLinkerBase, dsl_runner: DslRunner, cached_map: dict, debug_info: dict):
        super().__init__(nl_query, kg_graph, schema, debug_info)
        self.op_register_map = {
            'get': GetExecutor(nl_query, kg_graph, schema, el, dsl_runner, cached_map, self.debug_info)
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetNode)

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        op = self.op_register_map.get(logic_node.operator, None)
        if op is None:
            return []
        return op.executor(logic_node, req_id, param)
