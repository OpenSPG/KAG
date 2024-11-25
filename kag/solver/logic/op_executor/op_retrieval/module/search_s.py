from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.op_executor.op_executor import OpExecutor


class SearchS(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: Schema, debug_info: dict):
        super().__init__(nl_query, kg_graph, schema, debug_info)

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> KgGraph:
        raise NotImplementedError("search s not impl")