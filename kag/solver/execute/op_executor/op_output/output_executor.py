from typing import Dict

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.execute.op_executor.op_output.module.get_executor import GetExecutor
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import GetNode


class OutputExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.KAG_PROJECT_ID = kwargs.get("KAG_PROJECT_ID")
        self.op_register_map = {
            "get": GetExecutor(
                schema,
                **kwargs,
            )
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetNode)

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        op = self.op_register_map.get(logic_node.operator, None)
        if op is None:
            return {}
        return op.executor(nl_query, logic_node, req_id, kg_graph, process_info, param)
