import json
import logging
import re
import time
import concurrent.futures
from abc import ABC
from typing import List

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.interface import LLMClient, VectorizeModelABC
from kag.interface.solver.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import (
    OneHopGraphData,
    KgGraph,
    EntityData,
)
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever
from kag.solver.tools.algorithm.entity_linker import (
    default_search_entity_by_name_algorithm,
)
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC, generate_gql_id_params
from kag.solver.tools.search_api.search_api_abc import SearchApiABC
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()


class FuzzyMatchRetrieval:
    def __init__(self, llm: LLMClient, text_similarity: TextSimilarity):
        self.llm: LLMClient = llm
        self.text_similarity: TextSimilarity = text_similarity
        self.cached_map = {}

        self.biz_scene = KAG_PROJECT_CONF.biz_scene
        self.language = KAG_PROJECT_CONF.language

    def get_unstd_p_text(self, n: GetSPONode):
        un_std_p = n.p.get_entity_first_type_or_un_std()
        if un_std_p is None:
            logger.warning(f"get_unstd_p_text get p emtpy {n}")
            un_std_p = ""
        start_value_type = n.s.get_entity_first_type_or_un_std()
        if start_value_type is None or start_value_type == "Others":
            logger.debug(
                f"get_unstd_p_text get start_value_type {start_value_type} {n}"
            )
            start_value_type = "Entity"
        target_value_type = n.o.get_entity_first_type_or_un_std()
        if target_value_type is None or target_value_type == "Others":
            logger.debug(
                f"get_unstd_p_text get target_value_type {target_value_type} {n}"
            )
            target_value_type = "Entity"
        un_std_p = f"{start_value_type}{'[' + n.get_ele_name('s') + ']' if n.get_ele_name('s') != '' else ''} {un_std_p} {target_value_type}{'[' + n.get_ele_name('o') + ']'}"
        return un_std_p

    def _choosed_by_llm(self, question, mention, candis):
        resp_plan_prompt = init_prompt_with_fallback("spo_retrieval", self.biz_scene)

        return self.llm.invoke(
            {"question": question, "mention": mention, "candis": candis},
            resp_plan_prompt,
            with_json_parse=True,
            with_except=True,
        )

    def select_relation(self, p_mention, p_candis, query=""):
        if not p_mention:
            print("p_mention is none")
            return None
        if p_mention in self.cached_map.keys():
            cached_set = self.cached_map[p_mention]
            intersection = list(set(cached_set) & set(p_candis))
        else:
            intersection = []
        if len(intersection) == 0:
            res = ""
            try:
                res = self._choosed_by_llm(query, p_mention, p_candis)
                for res_ in res:
                    self.cached_map[p_mention] = self.cached_map.get(p_mention, []) + [
                        res_
                    ]
                    intersection.append(res_)
            except Exception as e:
                logger.warning(
                    f"retrieval_spo json failed：query={query},  res={res} , except={e}",
                    exc_info=True,
                )
        return [[x, 1.0] for x in intersection]

    def find_best_match_p_name_by_model(self, query: str, p: str, candi_set: dict):
        if p in candi_set:
            return [p, candi_set[p]]
        spo_retrieved = []
        sen_condi_set = []
        spo_name_map = {}
        for p_name, spo_l in candi_set.items():
            if (
                p_name.startswith("_")
                or p_name == "id"
                or p_name == "source"
                or p_name == "similar"
            ):
                continue
            for spo in spo_l:
                spo_name_map[spo] = p_name
            sen_condi_set += spo_l
        result = self.select_relation(p, sen_condi_set, query=query)
        logger.debug(
            f"retrieval_relation: p={p}, candi_set={sen_condi_set}, p_std result={result}"
        )

        if result is None or len(result) == 0:
            return spo_retrieved

        for result_ in result:
            spo = result_[0]
            spo_p_name = spo_name_map.get(spo, None)
            spo_retrieved.append([spo, spo_p_name])
        return spo_retrieved

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        one_kg_graph = KgGraph()
        # sort graph
        unstd_p_text = self.get_unstd_p_text(n)
        all_spo_text = []
        revert_value_p_map = {}
        revert_graph_map = {}
        for one_hop_graph in one_hop_graph_list:
            for k, v_set in one_hop_graph.get_s_all_relation_spo().items():
                for v in v_set:
                    all_spo_text.append(v)
                    revert_value_p_map[v] = k
                    revert_graph_map[v] = one_hop_graph
            for k, v_set in one_hop_graph.get_s_all_attribute_spo().items():
                for v in v_set:
                    attr_txt = f"{one_hop_graph.s.get_short_name()} {k} {v}"
                    all_spo_text.append(attr_txt)
                    revert_value_p_map[attr_txt] = k
                    revert_graph_map[attr_txt] = one_hop_graph
        start_time = time.time()
        tok5_res = self.text_similarity.text_sim_result(
            n.sub_query, all_spo_text, 5, low_score=0.3
        )
        logger.debug(
            f" _get_spo_value_in_one_hop_graph_set text similarity cost={time.time() - start_time}"
        )

        if len(tok5_res) == 0:
            return one_kg_graph
        candi_name_set = {}
        for res in tok5_res:
            k = revert_value_p_map[res[0]]
            if k in candi_name_set.keys():
                candi_name_set[k].append(res[0])
            else:
                candi_name_set[k] = [res[0]]
        start_time = time.time()
        spo_retrieved = self.find_best_match_p_name_by_model(
            n.sub_query, unstd_p_text, candi_name_set
        )
        logger.debug(
            f"_get_spo_value_in_one_hop_graph_set find_best_match_p_name_by_entity_list cost={time.time() - start_time}"
        )
        total_one_kg_graph = KgGraph()
        total_one_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name,
        }
        for std_spo_text, std_p in spo_retrieved:
            if std_p is None or std_p == "":
                continue
            one_hop_graph = revert_graph_map[std_spo_text]
            rel_set = one_hop_graph.get_std_p_value_by_spo_text(std_p, std_spo_text)
            one_kg_graph_ = KgGraph()
            recall_alias_name = (
                n.s.alias_name if one_hop_graph.s_alias_name == "s" else n.o.alias_name
            )
            one_kg_graph_.entity_map[recall_alias_name] = [one_hop_graph.s]
            one_kg_graph_.edge_map[n.p.alias_name] = rel_set
            total_one_kg_graph.merge_kg_graph(one_kg_graph_)
        return total_one_kg_graph


@FuzzyKgRetriever.register("default_fuzzy_kg_retriever", as_default=True)
class DefaultFuzzyKgRetriever(FuzzyKgRetriever, ABC):
    def __init__(
        self,
        el_num=1,
        llm_client: LLMClient = None,
        vectorize_model: VectorizeModelABC = None,
        graph_api: GraphApiABC = None,
        search_api: SearchApiABC = None,
        **kwargs,
    ):
        super().__init__(
            el_num, llm_client, vectorize_model, graph_api, search_api, **kwargs
        )
        self.match = FuzzyMatchRetrieval(self.llm_module, self.text_similarity)

    def recall_one_hop_graph(
        self, n: GetSPONode, heads: List[EntityData], tails: List[EntityData], **kwargs
    ) -> List[OneHopGraphData]:
        """
        Recall one-hop graph data for a given entity.

        Parameters:
            n (GetSPONode): The entity to be standardized.
            heads (List[EntityData]): A list of candidate entities 's'.
            tails (List[EntityData]): A list of candidate entities 'o'.
            kwargs: Additional optional parameters.

        Returns:
            List[OneHopGraphData]: A list of one-hop graph data for the given entity.
        """
        one_hop_graph_list = []
        try:
            if len(heads) > 0 and len(tails) > 0:
                header_ids = set(head.biz_id for head in heads)
                tail_ids = set(tail.biz_id for tail in tails)
                where_caluse = []
                header_labels = set(f"`{head.type}`" for head in heads)
                params = {}
                if not header_labels:
                    dsl_header_label = "Entity"
                else:
                    dsl_header_label = "|".join(header_labels)
                    params["sid"] = generate_gql_id_params(list(header_ids))
                    where_caluse.append(f"s.id in $sid")

                tail_labels = set(f"`{tail.type}`" for tail in tails)
                if not tail_labels:
                    dsl_tail_label = "Entity"
                else:
                    dsl_tail_label = "|".join(tail_labels)
                    params["oid"] = generate_gql_id_params(list(tail_ids))
                    where_caluse.append(f"o.id in $oid")
                try:
                    dsl = f"""
                    MATCH (s:{dsl_header_label})-[p:rdf_expand()]-(o:{dsl_tail_label})
                    WHERE {' and '.join(where_caluse)}
                    RETURN s,p,o,s.id,o.id
                    """
                    fat_table = self.graph_api.execute_dsl(dsl, **params)
                    one_graph_map = self.graph_api.convert_spo_to_one_graph(fat_table)
                    if len(one_graph_map) > 0:
                        return list(one_graph_map.values())
                except Exception as e:
                    logger.debug(
                        f"An error occurred: {e}, so we will call head and tail same time",
                        exc_info=True,
                    )

            with concurrent.futures.ThreadPoolExecutor() as executor:
                map_dict = {"s": heads, "o": tails}
                for k, v in map_dict.items():
                    futures = [
                        executor.submit(self.graph_api.get_entity_one_hop, entity)
                        for entity in v
                    ]
                    results = [
                        future.result()
                        for future in concurrent.futures.as_completed(futures)
                    ]
                    for r in results:
                        if r is None:
                            logger.debug(f"{n} recall chunk data")
                            continue
                        r.s_alias_name = k
                        one_hop_graph_list.append(r)
            return one_hop_graph_list
        except Exception as e:
            # Log the error or handle it appropriately
            logger.warning(f"An error occurred: {e}", exc_info=True)
            return one_hop_graph_list

    def retrieval_relation(
        self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData], **kwargs
    ) -> KgGraph:
        """
        Input:
            n: GetSPONode, the relation to be standardized
            one_hop_graph_list: List[OneHopGraphData], list of candidate sets
            kwargs: additional optional parameters

        Output:
            Returns KgGraph
        """
        start_time = time.time()
        total_one_kg_graph = self.match.match_spo(n, one_hop_graph_list)
        logger.debug(f"_exact_match_spo cost={time.time() - start_time}")
        return total_one_kg_graph

    def retrieval_entity(self, mention_entity: SPOEntity, **kwargs) -> List[EntityData]:
        """
        Retrieve related entities based on the given entity mention.

        This function aims to retrieve the most relevant entities from storage or an index based on the provided entity name.

        Parameters:
            entity_mention (str): The name of the entity to retrieve.
            kwargs: additional optional parameters

        Returns:
            list of EntityData
        """
        return default_search_entity_by_name_algorithm(
            mention_entity=mention_entity,
            schema=self.schema,
            vectorize_model=self.vectorize_model,
            text_similarity=self.text_similarity,
            search_api=self.search_api,
            topk=self.el_num,
            recognition_threshold=0.8,
            kwargs=kwargs,
        )
