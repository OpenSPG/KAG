import logging
from typing import Dict

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.execute.op_executor.op_retrieval.module.get_spo_executor import GetSPOExecutor
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode

logger = logging.getLogger()


class RetrievalExecutor(OpExecutor):
    def __init__(
        self,
        kg_graph: KgGraph,
        schema: SchemaUtils,
        process_info: dict,
        **kwargs
    ):
        super().__init__(kg_graph, schema, process_info, **kwargs)
        self.query_one_graph_cache = {}
        self.op_register_map = {
            "get_spo": GetSPOExecutor(
                kg_graph,
                schema,
                self.process_info,
                **kwargs,
            ),
            "search_s": SearchS(
                kg_graph,
                schema,
                self.process_info,
                **kwargs,
            ),
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetSPONode)

    def executor(self, nl_query: str, logic_node: LogicNode, req_id: str, param: dict) -> Dict:
        op = self.op_register_map.get(logic_node.operator, None)
        if op is None:
            return {}
        try:
            cur_kg_graph = op.executor(nl_query, logic_node, req_id, param)
            if cur_kg_graph is not None:
                self.kg_graph.merge_kg_graph(cur_kg_graph)
        except Exception as e:
            logger.warning(f"op {logic_node.operator} run failed! {e}", exc_info=True)
        return self.process_info.get(logic_node.sub_query, {})