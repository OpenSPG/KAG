#!/usr/bin/python
# coding=utf8
import concurrent.futures
import json
import logging

from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.logic.common.base_model import LogicNode
from kag.solver.logic.common.one_hop_graph import KgGraph, EntityData
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.common.text_sim_by_vector import TextSimilarity

logger = logging.getLogger()


class EntityLinkerBase:
    def __init__(self, config):
        self.config = config

    def entity_linking(self, content, entities, types=None, req_id='', **params):
        logger.info(f"EntityLinkerBase {req_id} return empty linker")
        return [
               ], []

    def get_service_name(self):
        return {
            'scene_name': '空链指调用'
        }


class Neo4jEntityLinker(EntityLinkerBase):
    def __init__(self, config, graph_store, kg_retriever: KGRetrieverABC):
        super().__init__(config)
        self.graph_store = graph_store
        self.recognition_threshold = float(0.8)
        self.text_similarity = TextSimilarity()
        self.kg_retriever = kg_retriever

    def get_service_name(self):
        return {
            'scene_name': 'neo4j'
        }

    def _call_feature(self, feature):
        query = feature.get('query_text', '')
        query_label = feature.get('label', 'Entity')
        # 向量召回相似name的Entity
        return self.kg_retriever.retrieval_entity(query, params={'label': query_label})

    def compose_features(self, content, entities, types=None, req_id='', params={}):
        features = []
        for i, entity in enumerate(entities):
            entity_str = f"{entity}"
            if types and i < len(types):
                subject_type = types[i]
            else:
                subject_type = "Entity"
            content = f"{content}[Entity]{entity_str}"
            feature = {
                "label": subject_type,
                "property_key": "name",
                'content': content,
                "query_text": entity_str,
                'recognition_threshold': self.recognition_threshold
            }
            feature.update(params)
            features.append(feature)
        return features

    def post_process(self, results, req_id, params):
        return results

    def entity_linking(self, content, entities, types=None, req_id='', **params):
        """
        input:
            content: str, context
            entities: [], entity spans to be linked
            types: [], entity types to be linked
        output:
            [{'content': '吉林省抚松县被人们称为是哪种药材之乡？', 'entities': [{'word': '吉林省抚松县', 'start_idx': 0, 'recall': []}]}
        """
        features = self.compose_features(content, entities, types, req_id, params)
        entity_recalls = {}
        logger.debug(f"{req_id} entity_linking {features}")
        call_datas = []
        if len(features) == 1:
            res = self._call_feature(features[0])
            call_datas.append({'res': res, 'recalls': entity_recalls})
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                call_datas = [{'res': [d], 'recalls': entity_recalls} for d in
                              list(executor.map(self._call_feature, features))]
        logger.debug(f'{req_id} entity_linking result: {call_datas}')
        results = []
        for data in call_datas:
            if isinstance(data, list):
                data_obj = data[0]['res']
            else:
                data_obj = data['res']
            if isinstance(data_obj, str):
                data_obj = json.loads(data_obj)
            if not isinstance(data_obj, list):
                data_obj = [data_obj]

            for recall_data in data_obj:
                results = results + recall_data['entities']

        return self.post_process(results, req_id, params), call_datas


def spo_entity_linker(
        kg_graph: KgGraph, n: LogicNode, nl_query,
        el: EntityLinkerBase, schema: Schema, req_id='', params={}
):
    el_results = []
    call_result_data = []
    arg_keys, entity_mentions, entity_mentions_type = [], [], []

    s_data = kg_graph.get_entity_by_alias(n.s.alias_name)
    if s_data is None and n.s.entity_name:
        arg_keys.append(n.s.alias_name)
        entity_mentions.append(n.s.entity_name)
        args_s_entity_type = n.s.get_entity_first_type_or_zh()
        if schema is not None:
            args_s_entity_type = '.'.join([schema.prefix, args_s_entity_type])
        entity_mentions_type.append(args_s_entity_type)

    el_kg_graph = KgGraph()
    if n.operator == 'get_spo':
        o_data = kg_graph.get_entity_by_alias(n.o.alias_name)
        if o_data is None and n.o.entity_name:
            arg_keys.append(n.o.alias_name)
            entity_mentions.append(n.o.entity_name)
            args_o_entity_type = n.o.get_entity_first_type_or_zh()
            if schema is not None:
                args_o_entity_type = '.'.join([schema.prefix, args_o_entity_type])
            entity_mentions_type.append(args_o_entity_type)
        el_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name
        }

    el_request = {
        "nl_query": nl_query,
        "entity_mentions": entity_mentions,
        "entity_mentions_type": entity_mentions_type
    }
    err_msg = ""
    if entity_mentions and el is not None:
        try:
            el_results, call_result_data = el.entity_linking(
                nl_query, entity_mentions, entity_mentions_type, req_id, **params
            )
        except Exception as e:
            logger.error(f"{req_id} spo_entity_linker error, we need use name to id {str(e)}", exc_info=True)
            el_results = []
            call_result_data = []
            err_msg = str(e)
        for i, (key, entity_mention, entity_mention_type) in enumerate(
                zip(arg_keys, entity_mentions, entity_mentions_type)
        ):
            entity_data_set = []
            if el_results and i < len(el_results) and 'recall' in el_results[i] and el_results[i]['recall']:
                el_recalls = el_results[i]['recall']
                for recall in el_recalls:
                    entity_name = recall['name']
                    entity_id = recall['subject_id']
                    entity_type = recall['type']
                    entity_type_zh = (
                        schema.node_en_zh[entity_type]
                        if schema is not None and entity_type in schema.node_en_zh.keys() else
                        None
                    )
                    entity_id_info = EntityData()
                    entity_id_info.biz_id = entity_id
                    entity_id_info.type = entity_type
                    entity_id_info.type_zh = entity_type_zh
                    entity_id_info.name = entity_name
                    entity_data_set.append(entity_id_info)
            else:
                entity_id_info = EntityData()
                entity_id_info.name = entity_mention
                entity_id_info.biz_id = entity_mention
                entity_id_info.type = "Entity"
                entity_type_zh = (
                    schema.node_en_zh[entity_id_info.type]
                    if schema is not None and entity_id_info.type in schema.node_en_zh.keys() else
                    None
                )
                entity_id_info.type_zh = entity_type_zh
                entity_data_set.append(entity_id_info)
            el_kg_graph.nodes_alias.append(key)
            el_kg_graph.entity_map[key] = entity_data_set

    kg_graph.merge_kg_graph(el_kg_graph, True)
    return el_results, el_request, err_msg, call_result_data
