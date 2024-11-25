from typing import Union

from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.op_executor.op_executor import OpExecutor
from kag.solver.logic.parser.logic_node_parser import FilterNode, VerifyNode, \
    ExtractorNode
from kag.solver.logic.rule_runner.rule_runner import OpRunner


class DeduceExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: Schema, rule_runner: OpRunner, debug_info: dict):
        super().__init__(nl_query, kg_graph, schema, debug_info)
        self.rule_runner = rule_runner
        self.op_register_map = {
            'verify': self.rule_runner.run_verify_op,
            'filter': self.rule_runner.run_filter_op,
            'extractor': self.rule_runner.run_extractor_op
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, (FilterNode, VerifyNode, ExtractorNode))

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        op_func = self.op_register_map.get(logic_node.operator, None)
        if op_func is None:
            return self.kg_graph
        return op_func(logic_node)
