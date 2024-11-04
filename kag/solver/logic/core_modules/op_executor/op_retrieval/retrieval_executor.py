import logging

from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.logic.core_modules.common.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.op_executor.op_retrieval.module.get_spo_executor import GetSPOExecutor
from kag.solver.logic.core_modules.op_executor.op_retrieval.module.search_s import SearchS
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.logic.core_modules.retriver.entity_linker import EntityLinkerBase
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner

logger = logging.getLogger()


class RetrievalExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, retrieval_spo: KGRetrieverABC, el: EntityLinkerBase,
                 dsl_runner: DslRunner, debug_info: dict, text_similarity: TextSimilarity=None,**kwargs):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)
        self.query_one_graph_cache = {}
        self.op_register_map = {
            'get_spo': GetSPOExecutor(nl_query, kg_graph, schema, retrieval_spo, el, dsl_runner, self.query_one_graph_cache, self.debug_info, text_similarity,KAG_PROJECT_ID = kwargs.get('KAG_PROJECT_ID')),
            'search_s': SearchS(nl_query, kg_graph, schema, self.debug_info,KAG_PROJECT_ID = kwargs.get('KAG_PROJECT_ID'))
        }

    def is_this_op(self, logic_node: LogicNode) -> bool:
        return isinstance(logic_node, GetSPONode)

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> KgGraph:
        op = self.op_register_map.get(logic_node.operator, None)
        if op is None:
            return KgGraph()
        try:
            cur_kg_graph = op.executor(logic_node, req_id, param)
            if cur_kg_graph is not None:
                self.kg_graph.merge_kg_graph(cur_kg_graph)
        except Exception as e:
            logger.warning(f"op {logic_node.operator} run failed! {e}", exc_info=True)
        return self.kg_graph
