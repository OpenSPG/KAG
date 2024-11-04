from typing import Union

from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.op_executor.op_output.module.get_executor import GetExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import GetNode
from kag.solver.logic.core_modules.retriver.entity_linker import EntityLinkerBase
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner


class OutputExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, el: EntityLinkerBase, dsl_runner: DslRunner, cached_map: dict, debug_info: dict, **kwargs):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)
        self.KAG_PROJECT_ID = kwargs.get('KAG_PROJECT_ID')
        self.op_register_map = {
            'get': GetExecutor(nl_query, kg_graph, schema, el, dsl_runner, cached_map, self.debug_info,KAG_PROJECT_ID = kwargs.get('KAG_PROJECT_ID'))
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetNode)

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> Union[KgGraph, list]:
        op = self.op_register_map.get(logic_node.operator, None)
        if op is None:
            return []
        return op.executor(logic_node, req_id, param)
