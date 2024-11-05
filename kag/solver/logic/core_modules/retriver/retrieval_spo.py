import json
import logging
import os
import re
import time
from typing import List

from kag.common.base.prompt_op import PromptOp
from kag.common.llm.client import LLMClient
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData, OneHopGraphData, \
    RelationData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode

logger = logging.getLogger()


def default_change_en_2_zh(s, p, o, schema: SchemaUtils):
    if schema is None:
        return p
    item = f"{s}_{p}_{o}"
    if item and item in schema.spo_en_zh.keys():
        return schema.get_spo_with_p(schema.spo_en_zh[item])
    item = f"{o}_{p}_{s}"
    if item and item in schema.spo_en_zh.keys():
        return schema.get_spo_with_p(schema.spo_en_zh[item])

    attr_en_zh = schema.get_attr_en_zh_by_label(s)
    if p in attr_en_zh.keys():
        return attr_en_zh[p]
    return p


def change_en_2_zh(s, p, o, schema: SchemaUtils):
    return f"{s}_{p}_{o}"


def split_value(value):
    value = value.strip()
    pattern = re.compile(r'[,、; ，]+')
    return pattern.split(value)


class RetrievalSpoBase:
    def __init__(self):
        pass

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        pass


class ExactMatchRetrievalSpo(RetrievalSpoBase):
    def __init__(self, schema):
        super().__init__()
        self.schema: SchemaUtils = schema

    def _prase_attribute_relation(self, one_graph, std_p: str, attr_value: str):
        # new a RelationData
        prop_entity = EntityData()
        prop_entity.biz_id = attr_value
        prop_entity.name = attr_value
        prop_entity.type = "attribute"
        prop_entity.type_zh = "文本"

        return self._prase_entity_relation(one_graph, std_p, prop_entity)

    def _prase_entity_relation(self, one_graph, std_p: str, o_value: EntityData):
        s_entity = one_graph.s
        o_entity = o_value
        if one_graph.s_alias_name == "o":
            o_entity = one_graph.s
            s_entity = o_value
        if o_value.description is None or o_value.description == '':
            o_value.description = f"{s_entity.name} {std_p} {o_entity.name}"
        return RelationData.from_prop_value(s_entity, std_p, o_entity)

    def _std_best_p_with_value_and_p_name(self, n: GetSPONode, one_graph: OneHopGraphData):
        """
        :param one_graph:
        :return: list(RelationData)
        """
        debug_info = {
            "el": [],
            "el_detail": [],
            "std_out": []
        }
        logger.debug(f"std_best_p_with_value_and_p_name begin std " + str(n))
        un_std_p_list = n.p.get_entity_type_or_zh_list()
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

        for un_std_p in un_std_p_list:
            target_value = n.o.entity_name if one_graph.s_alias_name == "s" else n.s.entity_name
            target_node = n.o if one_graph.s_alias_name == "s" else n.s
            relation_name_set = one_graph.get_s_all_relation_name()
            attribute_name_set = one_graph.get_s_all_attribute_name()
            candi_name_set = relation_name_set + attribute_name_set

            def find_best_match_p_name(p: str, candi_set: list):
                if p in candi_set:
                    return p
                return None

            std_p = find_best_match_p_name(un_std_p, candi_name_set)
            debug_info['std_out'].append({
                "un_std_p": un_std_p,
                "candi_name_set": candi_name_set,
                "std_p": std_p if std_p is not None else ''
            })
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
                logger.info(f"relation with el: un std p is " + un_std_p + ", std p is " + std_p)
                value = one_graph.get_std_attribute_value(std_p)
                if value is None or value == "":
                    continue
                # new a RelationData
                relation_data = [self._prase_attribute_relation(one_graph, std_p, value)]
            if target_value is not None:
                for r in relation_data:
                    candi_target_value = r.end_entity.name if one_graph.s_alias_name == "s" else r.start_entity.name
                    if candi_target_value == target_value:
                        final_result_list.append(r)
                        continue
            else:
                final_result_list = final_result_list + relation_data
        return final_result_list, debug_info

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        matched_flag = False
        one_kg_graph = KgGraph()
        one_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name
        }
        for tmp_one_hop_graph in one_hop_graph_list:
            rel_set, recall_debug_info = self._std_best_p_with_value_and_p_name(n, tmp_one_hop_graph)
            if len(rel_set) > 0:
                one_kg_graph_ = KgGraph()
                recall_alias_name = n.s.alias_name if tmp_one_hop_graph.s_alias_name == "s" else n.o.alias_name
                one_kg_graph_.entity_map[recall_alias_name] = [tmp_one_hop_graph.s]
                one_kg_graph_.edge_map[n.p.alias_name] = rel_set
                one_kg_graph.merge_kg_graph(one_kg_graph_)
        spo_set = one_kg_graph.get_entity_by_alias(n.p.alias_name)
        if spo_set is not None and len(spo_set) != 0:
            matched_flag = True
        return one_kg_graph, matched_flag


class FuzzyMatchRetrievalSpo(RetrievalSpoBase):
    def __init__(self, text_similarity: TextSimilarity = None, llm: LLMClient=None):
        super().__init__()
        model = os.getenv("KAG_LLM")
        self.llm: LLMClient = llm or LLMClient.from_config(eval(model))
        self.text_similarity = text_similarity or TextSimilarity()
        self.cached_map = {}

        self.biz_scene = os.getenv("KAG_PROMPT_BIZ_SCENE", "default")
        self.language = os.getenv("KAG_PROMPT_LANGUAGE", "en")

    def get_unstd_p_text(self, n: GetSPONode):
        un_std_p = n.p.get_entity_first_type_or_zh()
        start_value_type = n.s.get_entity_first_type_or_zh()
        if start_value_type == "Others":
            start_value_type = "Entity"
        target_value_type = n.o.get_entity_first_type_or_zh()
        if target_value_type == "Others":
            target_value_type = "Entity"
        un_std_p = f"{start_value_type}{'[' + n.s.entity_name + ']' if n.s.entity_name is not None else ''} {un_std_p} {target_value_type}{'[' + n.o.entity_name + ']' if n.o.entity_name is not None else ''}"
        return un_std_p

    def _choosed_by_llm(self, question, mention, candis):
        resp_plan_prompt = PromptOp.load(self.biz_scene, "spo_retrieval")(
            language=self.language
        )
        return self.llm.invoke({
            'question': question,
            'mention': mention,
            'candis': candis
        }, resp_plan_prompt, with_json_parse=False, with_except=True)

    def select_relation(self, p_mention, p_candis, query='', topk=1, params={}):
        if not p_mention:
            print('p_mention is none')
            return None
        if p_mention in self.cached_map.keys():
            cached_set = self.cached_map[p_mention]
            intersection = list(set(cached_set) & set(p_candis))
        else:
            intersection = []
        if len(intersection) == 0:
            res = ''
            try:
                res = self._choosed_by_llm(query, p_mention, p_candis)
                res = res.replace("Output:", "output:")
                if "output:" in res:
                    res = re.search('output:(.*)', res).group(1).strip()
                if res != '':
                    res = json.loads(res.replace("'", '"'))
                    for res_ in res:
                        self.cached_map[p_mention] = self.cached_map.get(p_mention, []) + [res_]
                        intersection.append(res_)
            except:
                logger.warning(f"retrieval_spo json failed：query={query},  res={res}")
        return [[x, 1.0] for x in intersection]

    def find_best_match_p_name_by_model(self, query: str, p: str, candi_set: dict):
        if p in candi_set:
            return [p, candi_set[p]]
        spo_retrieved = []
        sen_condi_set = []
        spo_name_map = {}
        for p_name, spo_l in candi_set.items():
            if p_name.startswith("_") or p_name == "id" or p_name == 'content':
                continue
            for spo in spo_l:
                spo_name_map[spo] = p_name
            sen_condi_set += spo_l
        result = self.select_relation(p, sen_condi_set, query=query)
        logger.debug(f"retrieval_relation: p={p}, candi_set={sen_condi_set}, p_std result={result}")

        if result is None or len(result) == 0:
            return spo_retrieved

        for result_ in result:
            spo = result_[0]
            spo_p_name = spo_name_map.get(spo, None)
            spo_retrieved.append([spo, spo_p_name])
        return spo_retrieved

    def match_spo(self, n: GetSPONode, one_hop_graph_list: List[OneHopGraphData]):
        matched_flag = False
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
                    all_spo_text.append(v)
                    revert_value_p_map[v] = k
                    revert_graph_map[v] = one_hop_graph
        start_time = time.time()
        tok5_res = self.text_similarity.text_sim_result(n.sub_query, all_spo_text, 5, low_score=0.3)
        logger.debug(f" _get_spo_value_in_one_hop_graph_set text similarity cost={time.time() - start_time}")

        if len(tok5_res) == 0:
            return one_kg_graph, matched_flag

        matched_flag = True

        candi_name_set = {}
        for res in tok5_res:
            k = revert_value_p_map[res[0]]
            if k in candi_name_set.keys():
                candi_name_set[k].append(res[0])
            else:
                candi_name_set[k] = [res[0]]
        start_time = time.time()
        spo_retrieved = self.find_best_match_p_name_by_model(n.sub_query, unstd_p_text,
                                                             candi_name_set)
        logger.debug(
            f"_get_spo_value_in_one_hop_graph_set find_best_match_p_name_by_entity_list cost={time.time() - start_time}")
        total_one_kg_graph = KgGraph()
        total_one_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name
        }
        for std_spo_text, std_p in spo_retrieved:
            if std_p is None or std_p == '':
                continue
            one_hop_graph = revert_graph_map[std_spo_text]
            rel_set = one_hop_graph.get_std_p_value_by_spo_text(std_p, std_spo_text)
            one_kg_graph_ = KgGraph()
            recall_alias_name = n.s.alias_name if one_hop_graph.s_alias_name == "s" else n.o.alias_name
            one_kg_graph_.entity_map[recall_alias_name] = [one_hop_graph.s]
            one_kg_graph_.edge_map[n.p.alias_name] = rel_set
            total_one_kg_graph.merge_kg_graph(one_kg_graph_)
        return total_one_kg_graph, matched_flag
