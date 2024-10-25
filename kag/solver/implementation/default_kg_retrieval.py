# coding=utf8
import os
import time
from typing import List

from knext.project.client import ProjectClient

from kag.common.vectorizer import Vectorizer
from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from knext.search.client import SearchClient
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, OneHopGraphData, EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.common.utils import get_recall_node_label, generate_biz_id_with_type
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode, ParseLogicForm
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner, DslRunnerOnGraphStore
from kag.solver.logic.core_modules.retriver.retrieval_spo import FuzzyMatchRetrievalSpo, ExactMatchRetrievalSpo

current_dir = os.path.dirname(os.path.abspath(__file__))
import logging

logger = logging.getLogger()


class KGRetrieverByLlm(KGRetrieverABC):
    """
    A subclass of KGRetrieval that implements relation and entity retrieval using large language models.

    This class provides the default implementation for retrieving relations and entities within the system,
    leveraging large language models for its operations.
    """

    def __init__(self, disable_exact_match=False, **kwargs):
        super().__init__(**kwargs)

        vectorizer_config = eval(os.getenv("KAG_VECTORIZER", "{}"))
        if self.host_addr and self.project_id:
            config = ProjectClient(host_addr=self.host_addr, project_id=self.project_id).get_config(self.project_id)
            vectorizer_config.update(config.get("vectorizer", {}))
        self.vectorizer: Vectorizer = Vectorizer.from_config(vectorizer_config)
        self.text_similarity = TextSimilarity(vec_config=vectorizer_config)
        self.schema = SchemaUtils(LogicFormConfiguration(kwargs))
        self.schema.get_schema()

        self.disable_exact_match = disable_exact_match

        self.sc: SearchClient = SearchClient(self.host_addr, self.project_id)
        self.dsl_runner: DslRunner = DslRunnerOnGraphStore(self.project_id, self.schema, LogicFormConfiguration(kwargs))

        self.fuzzy_match = FuzzyMatchRetrievalSpo(text_similarity=self.text_similarity, llm=self.llm_module)
        self.exact_match = ExactMatchRetrievalSpo(self.schema)
        self.parser = ParseLogicForm(self.schema, None)

    def retrieval_relation(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs) -> KgGraph:
        req_id = kwargs.get('req_id', '')
        debug_info = kwargs.get('debug_info', {})
        if not self.disable_exact_match:
            process_kg, is_matched = self._exact_match_spo(n, one_hop_graph_list, req_id)
            if is_matched:
                debug_info["exact_match_spo"] = True and debug_info.get('exact_match_spo', True)
                return process_kg
            else:
                debug_info["exact_match_spo"] = False
        return self._fuzzy_match_spo(n, one_hop_graph_list, req_id)

    def retrieval_entity(self, mention_entity: SPOEntity, topk=5, **kwargs) -> List[EntityData]:
        recalled_el_set = self._search_retrieval_entity(mention_entity, topk=topk, kwargs=kwargs)
        if len(mention_entity.value_list) == 0:
            return recalled_el_set
        # 存在参数进行过滤，先过去一跳子图
        one_hop_graph_map = self.dsl_runner.query_vertex_one_graph_by_s_o_ids(recalled_el_set, [], {})
        matched_entity_list = recalled_el_set
        # 将待匹配的作为spg进行匹配
        for k, v in mention_entity.value_list:
            choosed_one_hop_graph_list = self._get_matched_one_hop(one_hop_graph_map, matched_entity_list)
            param_spo = f"get_spo(s=s1:{mention_entity.get_entity_first_type_or_zh()}[{mention_entity.entity_name}],p=p1:{k},o=o1:Entity[{v}])"
            tmp_spo = self.parser.parse_logic_form(param_spo, parsed_entity_set={}, sub_query=f"{mention_entity.entity_name} {k} {v}")
            debug_info = {}
            kg_graph = self.retrieval_relation(tmp_spo, choosed_one_hop_graph_list, debug_info=debug_info)
            kg_graph.nodes_alias.append(tmp_spo.s.alias_name)
            kg_graph.nodes_alias.append(tmp_spo.o.alias_name)
            kg_graph.edge_alias.append(tmp_spo.p.alias_name)
            matched_entity_list = kg_graph.get_entity_by_alias("s1")
            if matched_entity_list is None:
                return []

        return matched_entity_list

    def _get_matched_one_hop(self, one_hop_graph_map: dict, matched_entity_list: list):
        ret_one_hop_list = []
        for matched_entity in matched_entity_list:
            cached_id = generate_biz_id_with_type(matched_entity.biz_id,
                                                  matched_entity.type_zh if matched_entity.type_zh else matched_entity.type)
            if cached_id in one_hop_graph_map:
                ret_one_hop_list.append(one_hop_graph_map[cached_id])
        return ret_one_hop_list

    def _search_retrieval_entity(self, mention_entity: SPOEntity, topk=5, **kwargs) -> List[EntityData]:
        retdata = []
        if mention_entity is None:
            return retdata
        content = kwargs.get('content', mention_entity.entity_name)
        query_type = mention_entity.get_entity_first_type_or_zh()
        recognition_threshold = kwargs.get('recognition_threshold', 0.8)
        recall_topk = topk
        if "entity" not in query_type.lower():
            recall_topk = 10
        query_vector = self.vectorizer.vectorize(mention_entity.entity_name)
        typed_nodes = self.sc.search_vector(
            label="Entity", property_key="name", query_vector=query_vector, topk=recall_topk
        )
        # 根据query召回
        if query_type not in ["Others", "Entity"]:
            content_vector = self.vectorizer.vectorize(content)
            content_recall_nodes = self.sc.search_vector(
                label="Entity", property_key="desc", query_vector=content_vector, topk=recall_topk
            )
        else:
            content_recall_nodes = []
        sorted_nodes = typed_nodes + content_recall_nodes
        if len(sorted_nodes) == 0:
            sorted_nodes = self.sc.search_text(query_string=mention_entity.entity_name)

        # rerank
        def rerank_sematic_type(cands_nodes: list, sematic_type: str):
            sematic_type_list = []
            for cands in cands_nodes:
                node = cands['node']
                if "semanticType" not in node.keys() or node['semanticType'] == '':
                    continue
                sematic_type_list.append(node['semanticType'])
            sematic_type_list = list(set(sematic_type_list))
            sematic_match_score_list = self.text_similarity.text_sim_result(sematic_type, sematic_type_list,
                                                                            len(sematic_type_list), low_score=-1)
            sematic_match_score_map = {}
            for i in sematic_match_score_list:
                sematic_match_score_map[i[0]] = i[1]
            for node in cands_nodes:
                recall_node_label = get_recall_node_label(node['node']['__labels__'])
                if recall_node_label == sematic_type:
                    node['type_match_score'] = node['score']
                elif "semanticType" not in node['node'].keys() or node['node']['semanticType'] == '':
                    node['type_match_score'] = 0.3
                else:
                    node['type_match_score'] = node['score'] * sematic_match_score_map[node['node']['semanticType']]
            sorted_people_dicts = sorted(cands_nodes, key=lambda node: node['type_match_score'], reverse=True)
            # 取top5
            return sorted_people_dicts[:topk]

        if "entity" not in query_type.lower():
            sorted_nodes = rerank_sematic_type(sorted_nodes, query_type)
        sorted_people_dicts = sorted(sorted_nodes, key=lambda node: node['score'], reverse=True)
        for recall in sorted_people_dicts:
            if len(sorted_people_dicts) != 0 and recall["score"] >= recognition_threshold:
                recalled_entity = EntityData()
                recalled_entity.score = recall["score"]
                recalled_entity.biz_id = recall["node"]["id"]
                recalled_entity.name = recall["node"]["name"]
                recalled_entity.type = get_recall_node_label(recall["node"]["__labels__"])
                retdata.append(recalled_entity)
            else:
                break
        return retdata[:topk]

    def _exact_match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], req_id: str):
        start_time = time.time()
        total_one_kg_graph, matched_flag = self.exact_match.match_spo(n, one_hop_graph_list)
        logger.debug(
            f"{req_id} _exact_match_spo cost={time.time() - start_time} matched_flag={matched_flag}")
        if not matched_flag:
            return total_one_kg_graph, matched_flag
        for alias_name in total_one_kg_graph.entity_map.keys():
            for e in total_one_kg_graph.entity_map[alias_name]:
                score = e.score
                if score < 0.9:
                    total_one_kg_graph.rmv_node_ins(alias_name, [e.biz_id])
                    return total_one_kg_graph, False
        return total_one_kg_graph, matched_flag

    def _fuzzy_match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], req_id: str):
        start_time = time.time()

        total_one_kg_graph, matched_flag = self.fuzzy_match.match_spo(n, one_hop_graph_list)
        logger.debug(
            f"{req_id} _fuzzy_match_spo cost={time.time() - start_time} matched_flag={matched_flag}")
        return total_one_kg_graph
