from typing import Dict

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils


class SearchS(OpExecutor):
    def __init__(
        self,
        kg_graph: KgGraph,
        schema: SchemaUtils,
        debug_info: dict,
        **kwargs
    ):
        super().__init__(kg_graph, schema, debug_info, **kwargs)

    def executor(self, nl_query: str,logic_node: LogicNode, req_id: str, param: dict) -> Dict:
        raise NotImplementedError("search s not impl")
