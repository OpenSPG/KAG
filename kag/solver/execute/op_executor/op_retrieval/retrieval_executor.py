import logging
from typing import Dict, List

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.solver.execute.op_executor.op_retrieval.module.get_spo_executor import (
    GetSPOExecutor,
)
from kag.solver.execute.op_executor.op_retrieval.module.search_s import SearchS
from kag.interface.solver.base_model import LogicNode, LFPlan
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode

logger = logging.getLogger()


class RetrievalExecutor(OpExecutor):
    def __init__(self, schema: SchemaUtils, **kwargs):
        super().__init__(schema, **kwargs)
        self.query_one_graph_cache = {}
        self.op_register_map = {
            "get_spo": GetSPOExecutor(
                schema,
                **kwargs,
            ),
            "search_s": SearchS(
                schema,
                **kwargs,
            ),
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetSPONode)

    def executor(self, nl_query: str, lf_plan: LFPlan, req_id: str, kg_graph: KgGraph, process_info: dict,
                 history: List[LFPlan], param: dict) -> Dict:
        op = self.op_register_map.get(lf_plan.lf_node.operator, None)
        if op is None:
            return {}
        try:
            op.executor(nl_query, lf_plan, req_id, kg_graph, process_info, history, param)
        except Exception as e:
            logger.warning(f"op {lf_plan.lf_node.operator} run failed! {e}", exc_info=True)
        return process_info.get(lf_plan.lf_node.sub_query, {})
