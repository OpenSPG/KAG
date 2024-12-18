from typing import Union

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import CountNode, SumNode


class MathExecutor(OpExecutor):
    def __init__(
        self,
        kg_graph: KgGraph,
        schema: SchemaUtils,
        process_info: dict,
        **kwargs
    ):
        super().__init__(kg_graph, schema, process_info, **kwargs)

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, (CountNode, SumNode))

    def executor(
        self, nl_query: str, logic_node: LogicNode, req_id: str, param: dict
    ) -> Union[KgGraph, list]:
        pass
