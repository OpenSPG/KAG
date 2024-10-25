#!/usr/bin/python
# coding=utf8
import concurrent.futures
import logging
from typing import List, Union

from kag.interface.retriever.kg_retriever_abc import KGRetrieverABC
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode, GetNode

logger = logging.getLogger()


class EntityLinkerBase:
    def __init__(self, config):
        self.config = config

    def entity_linking(self, content, entities: List[SPOEntity], req_id='', **kwargs):
        logger.info(f"EntityLinkerBase {req_id} return empty linker")
        return [
               ], []

    def get_service_name(self):
        return {
            'scene_name': '空链指调用'
        }


class DefaultEntityLinker(EntityLinkerBase):
    def __init__(self, config, kg_retriever: KGRetrieverABC):
        super().__init__(config)
        self.recognition_threshold = float(0.8)
        self.kg_retriever = kg_retriever

    def get_service_name(self):
        return {
            'scene_name': 'neo4j'
        }

    def _call_feature(self, feature):
        mention_entity = feature.get('mention_entity', None)
        return self.kg_retriever.retrieval_entity(mention_entity, params=feature)

    def compose_features(self, content, entities: List[SPOEntity], req_id='', params={}):
        features = []
        for i, entity in enumerate(entities):
            content = f"{content}[Entity]{entity.entity_name}"
            feature = {
                "mention_entity": entity,
                "property_key": "name",
                'content': content,
                "query_text": entity.entity_name,
                'recognition_threshold': self.recognition_threshold
            }
            feature.update(params)
            features.append(feature)
        return features

    ## ha3召回+精排链指
    def entity_linking(self, content, entities: List[SPOEntity], req_id='', **kwargs):
        '''
        input:
            content: str, context
            entities: [], entity spans to be linked
            types: [], entity types to be linked
        output:
            [{'content': '吉林省抚松县被人们称为是哪种药材之乡？', 'entities': [{'word': '吉林省抚松县', 'start_idx': 0, 'recall': []}]}
        '''
        features = self.compose_features(content, entities, req_id, kwargs)
        entity_recalls = {}
        logger.debug(f"{req_id} entity_linking {features}")
        call_datas = []
        if len(features) == 1:
            res = self._call_feature(features[0])
            call_datas.append({'res': res, 'recalls': entity_recalls, 'content': content})
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                call_datas = [{'res': d, 'recalls': entity_recalls, 'content': content} for d in
                              list(executor.map(self._call_feature, features))]
        logger.debug(f'{req_id} entity_linking result: {call_datas}')
        results = []
        for data in call_datas:
            recalled_entities = data['res']
            results.append(recalled_entities)
        return results, call_datas


def spo_entity_linker(kg_graph: KgGraph, n: Union[GetSPONode, GetNode], nl_query, el: EntityLinkerBase, schema: SchemaUtils, req_id='',
                      params={}):
    el_results = []
    call_result_data = []
    entities_candis = []
    args_entity_mentions = [[], [], []]  # [keys, entities_name, entities_type]
    s_data = kg_graph.get_entity_by_alias(n.s.alias_name)
    if s_data is None and isinstance(n.s, SPOEntity) and n.s.entity_name and len(n.s.id_set) == 0:
        entities_candis.append(n.s)

    el_kg_graph = KgGraph()
    if isinstance(n, GetSPONode):
        o_data = kg_graph.get_entity_by_alias(n.o.alias_name)
        if o_data is None and isinstance(n.o, SPOEntity) and n.o.entity_name and len(n.o.id_set) == 0:
            entities_candis.append(n.o)
        el_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name
        }

    el_request = {
        "nl_query": nl_query,
        "entity_mentions": entities_candis
    }
    err_msg = ""
    if entities_candis and el is not None:
        try:
            el_results, call_result_data = el.entity_linking(nl_query, entities_candis, req_id, kwargs=params)
        except Exception as e:
            logger.error(f"{req_id} spo_entity_linker error, we need use name to id {str(e)}", exc_info=True)
            el_results = []
            call_result_data = []
            err_msg = str(e)
        for i in range(len(entities_candis)):
            candis_entitiy = entities_candis[i]
            entity_data_set = []
            if el_results and i < len(el_results) and el_results[i] is not None and len(el_results[i]) > 0:
                el_recalls = el_results[i]
                for entity_id_info in el_recalls:
                    entity_type_zh = schema.node_en_zh[
                        entity_id_info.type] if schema is not None and entity_id_info.type in schema.node_en_zh.keys() else None
                    entity_id_info.type_zh = entity_type_zh
                    entity_data_set.append(entity_id_info)
            else:
                entity_id_info = EntityData()
                entity_id_info.name = candis_entitiy.entity_name
                entity_id_info.biz_id = candis_entitiy.entity_name
                entity_id_info.type = schema.get_label_within_prefix(candis_entitiy.get_entity_first_type())
                entity_type_zh = schema.node_en_zh[
                    entity_id_info.type] if schema is not None and entity_id_info.type in schema.node_en_zh.keys() else None
                entity_id_info.type_zh = entity_type_zh
                entity_data_set.append(entity_id_info)
            el_kg_graph.nodes_alias.append(candis_entitiy.alias_name)
            el_kg_graph.entity_map[candis_entitiy.alias_name] = entity_data_set

    kg_graph.merge_kg_graph(el_kg_graph, True)
    return el_results, el_request, err_msg, call_result_data
