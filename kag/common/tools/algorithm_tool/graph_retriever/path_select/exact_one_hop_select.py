import logging
import time
from typing import List

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import VectorizeModelABC
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    RelationData,
    OneHopGraphData,
    parse_attribute_relation,
)
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.text_sim_by_vector import TextSimilarity
from kag.common.config import LogicFormConfiguration
from kag.common.parser.logic_node_parser import GetSPONode
from kag.common.tools.graph_api.graph_api_abc import (
    GraphApiABC,
)
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_utils import (
    run_gql,
    generate_gql_spo_element,
)

logger = logging.getLogger()


@PathSelect.register("exact_one_hop_select")
class ExactOneHopSelect(PathSelect):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        **kwargs,
    ):
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": kag_project_config.host_addr,
                }
            )
        )
        self.graph_api = graph_api or GraphApiABC.from_config(
            {"type": "openspg_graph_api"}
        )

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

    def recall_one_graph(
        self, gql_header_labels, gql_tail_labels, id_filters, **kwargs
    ) -> List[OneHopGraphData]:
        spg_gql = f"""
        MATCH (s:{gql_header_labels})-[p:rdf_expand()]->(o:{gql_tail_labels})
        WHERE {' and '.join(id_filters)}
        RETURN s,p,o,s.id,o.id
        """
        return run_gql(self.graph_api, spg_gql, **kwargs)

    def recall_by_spg_gql(
        self, gql_header_labels, gql_tail_labels, p_label_set, id_filters, **kwargs
    ) -> List[OneHopGraphData]:
        spg_gql = f"""
                MATCH (s:{gql_header_labels})-[p:{'|'.join(p_label_set)}]->(o:{gql_tail_labels})
                WHERE {' and '.join(id_filters)}
                RETURN s,p,o,s.id,o.id
                """
        return run_gql(self.graph_api, spg_gql, **kwargs)

    def recall_graph_data_from_knowledge_base(
        self, n: GetSPONode, heads: List[EntityData], tails: List[EntityData]
    ) -> List[OneHopGraphData]:
        (
            gql_header_labels,
            gql_rel_labels,
            gql_tail_labels,
            where_gql,
            params,
        ) = generate_gql_spo_element(n, heads, tails, self.schema_helper)

        if len(gql_rel_labels) == 0:
            return []
        try:
            gql_result = self.recall_by_spg_gql(
                gql_header_labels, gql_tail_labels, gql_rel_labels, where_gql, **params
            )
            if len(gql_result) != 0:
                return gql_result
        except Exception as e:
            logger.warning(f"recall_by_spg_gql failed {e},", exc_info=True)

        return []

    def _std_best_p_with_value_and_p_name(
        self, n: GetSPONode, one_graph: OneHopGraphData
    ):
        """
        :param one_graph:
        :return: list(RelationData)
        """
        logger.debug("std_best_p_with_value_and_p_name begin std " + str(n))
        un_std_p_list = n.p.get_entity_type_or_un_std_list()
        final_result_list = []
        if len(un_std_p_list) == 0:
            # return all
            result = []
            if len(one_graph.in_relations) > 0:
                for k in one_graph.in_relations.keys():
                    result = one_graph.in_relations[k] + result
            if len(one_graph.out_relations) > 0:
                for k in one_graph.out_relations.keys():
                    result = one_graph.out_relations[k] + result
            final_result_list = final_result_list + result

        if one_graph.s_alias_name == "s":
            target_value = n.o.get_mention_name()
            target_node = n.o
        else:
            target_value = n.s.get_mention_name()
            target_node = n.s
        for un_std_p in un_std_p_list:
            relation_name_set = one_graph.get_s_all_relation_name()
            attribute_name_set = one_graph.get_s_all_attribute_name()
            candi_name_set = relation_name_set + attribute_name_set

            def find_best_match_p_name(p: str, candi_set: list):
                if p in candi_set:
                    return p
                return None

            std_p = find_best_match_p_name(un_std_p, candi_name_set)
            if std_p is None:
                continue

            get_data_from_rel = False
            if std_p in relation_name_set and std_p in attribute_name_set:
                if not target_node.is_attribute:
                    get_data_from_rel = True
            elif std_p in relation_name_set:
                get_data_from_rel = True

            if get_data_from_rel:
                relation_data = one_graph.get_std_relation_value(std_p)
            else:
                logger.info(
                    "relation with el: un std p is " + un_std_p + ", std p is " + std_p
                )
                value = one_graph.get_std_attribute_value(std_p)
                if value is None or value == "":
                    continue
                # new a RelationData
                relation_data = [parse_attribute_relation(one_graph, std_p, value)]
            if target_value is not None:
                for r in relation_data:
                    candi_target_value = (
                        r.end_entity.name
                        if one_graph.s_alias_name == "s"
                        else r.from_entity.name
                    )
                    if candi_target_value == target_value:
                        final_result_list.append(r)
                        continue
            else:
                final_result_list = final_result_list + relation_data
        return final_result_list

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        result = []
        for tmp_one_hop_graph in one_hop_graph_list:
            rel_set = self._std_best_p_with_value_and_p_name(n, tmp_one_hop_graph)
            result += rel_set
        return result

    def invoke(
        self,
        query,
        spo: GetSPONode,
        heads: List[EntityData],
        tails: List[EntityData],
        **kwargs,
    ) -> List[RelationData]:
        begin_time = time.time()
        one_hop_graph_list = self.recall_graph_data_from_knowledge_base(
            spo, heads, tails
        )
        start_time = time.time()
        selected_rels = self.match_spo(spo, one_hop_graph_list)
        logger.info(
            f"_exact_match_spo total cost={time.time() - begin_time} cost={time.time() - start_time} selected_rels={len(selected_rels)}"
        )
        return selected_rels
