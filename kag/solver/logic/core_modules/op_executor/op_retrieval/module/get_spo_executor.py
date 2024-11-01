import logging
import time
from typing import List

from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.logic.core_modules.common.base_model import SPOEntity, LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData, RelationData, \
    OneHopGraphData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.logic.core_modules.retriver.entity_linker import EntityLinkerBase, spo_entity_linker
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner

logger = logging.getLogger()


class GetSPOExecutor(OpExecutor):
    """
    Executor for the 'get_spo' operator.

    This class is used to retrieve one-hop graphs based on the given parameters.
    It extends the base `OpExecutor` class and initializes additional components specific to retrieving SPO triples.
    """
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, retrieval_spo: KGRetrieverABC,
                 el: EntityLinkerBase,
                 dsl_runner: DslRunner, query_one_graph_cache: dict, debug_info: dict, text_similarity: TextSimilarity=None,**kwargs):
        """
        Initializes the GetSPOExecutor with necessary components.

        Parameters:
            nl_query (str): Natural language query string.
            kg_graph (KgGraph): Knowledge graph object for subsequent queries and parsing.
            schema (SchemaUtils): Semantic structure definition to assist in the parsing process.
            retrieval_spo (KGRetrieverABC): Retrieval object for SPO triples.
            el (EntityLinkerBase): Entity linker for entity linking tasks.
            dsl_runner (DslRunner): Runner cypher for query graph database.
            query_one_graph_cache (dict): Cache for storing results of one-hop graph queries.
            debug_info (dict): Debug information dictionary to record debugging information during parsing.
        """
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)
        self.retrieval_spo = retrieval_spo
        self.dsl_runner = dsl_runner
        self.query_one_graph_cache = query_one_graph_cache
        self.el = el

        self.text_similarity = text_similarity or TextSimilarity()

    def _find_relation_result(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], req_id: str):
        one_kg_graph = KgGraph()
        is_find_relation = False
        if n.p.get_entity_first_type_or_zh() is None and n.o.get_entity_first_type_or_zh() is None:
            is_find_relation = True
            for one_hop_graph in one_hop_graph_list:
                rel_set = one_hop_graph.get_all_relation_value()
                one_kg_graph_ = KgGraph()
                recall_alias_name = n.s.alias_name if one_hop_graph.s_alias_name == "s" else n.o.alias_name
                one_kg_graph_.entity_map[recall_alias_name] = [one_hop_graph.s]
                one_kg_graph_.edge_map[n.p.alias_name] = rel_set
                one_kg_graph.merge_kg_graph(one_kg_graph_)
        return one_kg_graph, is_find_relation

    def _get_spo_value_in_one_hop_graph_set(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], req_id: str):
        process_kg, is_rel = self._find_relation_result(n, one_hop_graph_list, req_id)
        if is_rel:
            return process_kg
        return self.retrieval_spo.retrieval_relation(n, one_hop_graph_list, req_id=req_id, debug_info = self.debug_info)

    def _run_query_vertex_one_graph(self, s_node_set: List[EntityData], o_node_set: List[EntityData], n: GetSPONode=None):
        return self.dsl_runner.query_vertex_one_graph_by_s_o_ids(s_node_set,
                                                                 o_node_set,
                                                                 self.query_one_graph_cache, n)

    def _execute_get_spo_by_set(self, n: GetSPONode, s_node_set: List[EntityData], o_node_set: List[EntityData], req_id):
        start_time = time.time()
        kg_graph = KgGraph()
        kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name
        }

        if (s_node_set is None or len(s_node_set) == 0) and (o_node_set is None or len(o_node_set) == 0):
            logger.info(f"{req_id} not found id is spo " + str(n))
            return kg_graph
        one_hop_graph_map = self._run_query_vertex_one_graph(s_node_set, o_node_set, n)
        end_time = time.time()
        logger.debug(f"{req_id} execute_get_spo_by_set {n} recall subgraph cost {end_time - start_time}")
        if len(one_hop_graph_map) == 0:
            logger.debug(f"{req_id} execute_get_spo_by_set one_hop_graph_map is empty")
            return kg_graph
        kg_graph.nodes_alias.append(n.s.alias_name)
        kg_graph.nodes_alias.append(n.o.alias_name)
        kg_graph.edge_alias.append(n.p.alias_name)

        start_time = time.time()
        one_hop_graph_list = []
        for biz_id in one_hop_graph_map.keys():
            self.query_one_graph_cache[biz_id] = one_hop_graph_map[biz_id]
            one_hop_graph_list.append(one_hop_graph_map[biz_id])

        res = self._get_spo_value_in_one_hop_graph_set(n, one_hop_graph_list, req_id)
        kg_graph.merge_kg_graph(res)

        logger.debug(
            f"{req_id} execute_get_spo_by_set merged kg graph ={kg_graph.to_edge_str()} cost = {time.time() - start_time}")
        return kg_graph

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> KgGraph:
        kg_graph = KgGraph()
        if not isinstance(logic_node, GetSPONode):
            return kg_graph
        n = logic_node

        self.kg_graph.logic_form_base[n.s.alias_name] = n.s
        self.kg_graph.logic_form_base[n.p.alias_name] = n.p
        self.kg_graph.logic_form_base[n.o.alias_name] = n.o

        # 实体标准化, 针对有实体名称的节点，需要做链指
        el_results, el_request, err_msg, call_result_data = spo_entity_linker(self.kg_graph,
                                                                              n,
                                                                              self.nl_query,
                                                                              self.el,
                                                                              self.schema,
                                                                              req_id,
                                                                              param)
        if el_request and el_request['entity_mentions']:
            self.debug_info['el'] = self.debug_info['el'] + el_results
            self.debug_info['el_detail'] = self.debug_info['el_detail'] + [{
                "el_request": el_request,
                'el_results': el_results,
                'el_debug_result': call_result_data,
                'err_msg': err_msg
            }]
            n.to_std(n.args)

        s_data_set = []
        relation_data_set = []

        if isinstance(n.s, SPOEntity) and len(n.s.id_set) > 0:
            s_data_set = self._get_entity_node_from_lf(n.s)
        else:
            s_data_set_up = self.kg_graph.get_entity_by_alias(n.s.alias_name)
            if s_data_set_up is not None:
                for s_data in s_data_set_up:
                    if isinstance(s_data, EntityData) and s_data.type != "attribute":
                        s_data_set.append(s_data)
                    if isinstance(s_data, RelationData):
                        relation_data_set.append(s_data)

        if len(relation_data_set) > 0:
            logger.info(f"{req_id} get_spo relation_data_set is not empty {str(relation_data_set)}, need get prop")
            return kg_graph

        o_data_set = []
        if n.o:
            if isinstance(n.o, SPOEntity) and len(n.o.id_set) > 0:
                o_data_set = self._get_entity_node_from_lf(n.o)
            else:
                o_data_set_up = self.kg_graph.get_entity_by_alias(n.o.alias_name)
                if o_data_set_up is not None:
                    for o_data in o_data_set_up:
                        o_data_set.append(o_data)
        cur_spo_graph = None
        if s_data_set:
            cur_spo_graph = self._execute_get_spo_by_set(n, s_data_set, [], req_id)
        if o_data_set:
            cur_spo_graph_o = self._execute_get_spo_by_set(n, [], o_data_set, req_id)
            if cur_spo_graph is None:
                cur_spo_graph = cur_spo_graph_o
            else:
                cur_spo_graph.merge_kg_graph(cur_spo_graph_o)
        kg_graph = cur_spo_graph
        return kg_graph

    def _get_entity_node_from_lf(self, e: SPOEntity):
        if not e.id_set:
            return []
        ret = []
        for biz_id in e.id_set:
            d = EntityData()
            d.biz_id = biz_id
            d.type = e.get_entity_first_type()
            d.type_zh = e.get_entity_first_type_or_en()
            ret.append(d)
        return ret