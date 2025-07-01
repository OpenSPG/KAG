import logging
import time
from typing import List, Dict

from kag.common.conf import KAGConstants, KAGConfigAccessor

from knext.graph.client import GraphClient
from knext.reasoner.rest.models.reason_task import ReasonTask

from kag.interface.solver.base_model import SPOEntity, TypeInfo
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    OneHopGraphData,
    Prop,
    RelationData,
    copy_one_hop_graph_data,
)
from kag.common.config import LogicFormConfiguration
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.utils import generate_biz_id_with_type
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC, generate_gql_id_params
from kag.common.tools.graph_api.model.table_model import TableData
from knext.reasoner.client import ReasonerClient
import knext.common.cache

logger = logging.getLogger()
entities_query_map = knext.common.cache.LinkCache(maxsize=1000, ttl=3000)


def update_cached_one_hop_rel(rel_dict: dict, rel: RelationData):
    rel_set = rel_dict.get(rel.type, [])
    rel_set.append(rel)
    rel_dict[rel.type] = rel_set
    return rel_dict


def convert_edge_to_json(p_str):
    try:
        import json

        p = json.loads(p_str)
    except Exception as e:
        logger.debug(f"_convert_edge_to_json failed {p_str}, {e}", exc_info=True)
        return {}
    prop = dict(p)
    return {"type": p["__label__"], "propertyValues": prop}


def convert_node_to_json(node_str):
    try:
        import json

        node = json.loads(node_str)
    except Exception as e:
        logger.debug(f"_convert_node_to_json failed {node_str}, {e}", exc_info=True)
        return {}
    return {
        "id": node["id"],
        "type": node["__label__"],
        "propertyValues": dict(node),
    }


@GraphApiABC.register("openspg_graph_api", as_default=True)
class OpenSPGGraphApi(GraphApiABC):
    def __init__(self, project_id=None, host_addr=None, **kwargs):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.project_id = project_id or kag_project_config.project_id
        self.host_addr = host_addr or kag_project_config.host_addr
        if self.project_id is not None and self.host_addr is not None:
            self.schema: SchemaUtils = SchemaUtils(
                LogicFormConfiguration(
                    {
                        "KAG_PROJECT_ID": str(self.project_id),
                        "KAG_PROJECT_HOST_ADDR": self.host_addr,
                    }
                )
            )

            self.rc = ReasonerClient(self.host_addr, int(str(self.project_id)))
            self.gr = GraphClient(self.host_addr, int(str(self.project_id)))
        else:
            self.rc = None
            self.gr = None

        self.cache_one_hop_graph: [str, OneHopGraphData] = {}

    def _get_cached_one_hop_graph(self, s_biz_id, s_type_name, cached_map: dict):
        s_biz_id_with_type_name = generate_biz_id_with_type(s_biz_id, s_type_name)
        return cached_map.get(s_biz_id_with_type_name, None)

    def _put_one_hop_graph_cache(self, one_hop: OneHopGraphData, cached_map: dict):
        s_biz_id_with_type_name = generate_biz_id_with_type(
            one_hop.s.biz_id, one_hop.s.type
        )
        cached_map[s_biz_id_with_type_name] = one_hop

    def _get_node_type_zh(self, s_type_name):
        s_type_without_prefix = self.schema.get_label_without_prefix(s_type_name)
        return self.schema.node_en_zh.get(s_type_without_prefix, s_type_without_prefix)

    def _convert_json_to_entity(
        self, s_json: dict, enable_cache: bool, cached_map: dict
    ) -> EntityData:
        prop_values = s_json["propertyValues"]
        s_biz_id = prop_values["id"]
        s_type_name = s_json["type"]

        one_hop: OneHopGraphData = self._get_cached_one_hop_graph(
            s_biz_id, s_type_name, cached_map
        )
        if one_hop:
            s_entity = one_hop.s
        else:
            s_entity = EntityData()
            s_entity.type = s_type_name
            s_entity.type_zh = self._get_node_type_zh(s_type_name)
            s_entity.prop = Prop.from_dict(prop_values, s_entity.type, self.schema)
            s_entity.biz_id = s_biz_id
            s_entity.name = prop_values.get("name", "")
            s_entity.description = prop_values.get("description", "")
            one_hop = OneHopGraphData(None, "s")
            one_hop.s = s_entity
            if enable_cache:
                self._put_one_hop_graph_cache(one_hop, cached_map)
        return s_entity

    def _convert_json_to_rel(
        self, p_json: dict, start_node: EntityData, end_node: EntityData
    ) -> RelationData:
        p_info = p_json["propertyValues"]
        rel = RelationData.from_dict(p_info, self.schema)
        s_id = generate_biz_id_with_type(start_node.biz_id, start_node.type)
        rel_s_id = generate_biz_id_with_type(rel.from_id, rel.from_type)

        rel.from_entity = start_node if rel_s_id == s_id else end_node
        rel.end_entity = end_node if rel_s_id == s_id else start_node
        return rel

    def convert_raw_data_to_node(
        self, data: str, enable_cache, cached_map
    ) -> EntityData:
        data_json = convert_node_to_json(data)
        return self._convert_json_to_entity(data_json, enable_cache, cached_map)

    def convert_raw_data_to_rel(
        self, data: str, start_node: EntityData, end_node: EntityData
    ) -> RelationData:
        return self._convert_json_to_rel(
            convert_edge_to_json(data), start_node, end_node
        )

    def get_entity(self, entity: SPOEntity) -> List[EntityData]:
        entity_type_list = entity.get_entity_type_set()
        entity_type_list_with_prefix = []
        for entity_type in entity_type_list:
            entity_type_list_with_prefix.append(
                f"`{self.schema.get_label_within_prefix(entity_type)}`"
            )
        entity_labels = "|".join(entity_type_list_with_prefix)
        n_id_param = generate_gql_id_params(entity.id_set)
        id_set = []
        for entity_id in entity.id_set:
            id_set.append(f'"{entity_id}"')
        dsl_query = f"""
        MATCH (n:{entity_labels})
        WHERE n.id in $nid
        RETURN n,n.id
        """
        tables: TableData = self.execute_dsl(dsl_query, nid=n_id_param)
        return [self.convert_raw_data_to_node(row[0], False, {}) for row in tables.data]

    def get_entity_one_hop(self, entity: EntityData) -> OneHopGraphData:
        start_time = time.time()
        s_id_param = generate_gql_id_params([entity.biz_id])
        dsl_query = f"""
        MATCH (s:`{entity.type}`)-[p:rdf_expand()]-(o:Entity)
        WHERE s.id in $sid
        RETURN s,p,o,s.id,o.id
        """
        s_biz_id_with_type_name = generate_biz_id_with_type(entity.biz_id, entity.type)
        one_hop: OneHopGraphData = entities_query_map.get(s_biz_id_with_type_name)
        if not one_hop:
            try:
                table: TableData = self.execute_dsl(dsl_query, sid=s_id_param)
                cached_map = self.convert_spo_to_one_graph(table)
                self.cache_one_hop_graph.update(cached_map)
                one_hop = self._get_cached_one_hop_graph(
                    entity.biz_id, entity.type, self.cache_one_hop_graph
                )
                entities_query_map.put(s_biz_id_with_type_name, one_hop)
            except Exception as e:
                logger.info(f"get_entity_one_hop failed! {e}", exc_info=True)

        if one_hop is None:
            logger.debug(f"get_entity_one_hop failed! {dsl_query}")
            return None
        logger.debug(f"get_entity_one_hop  cost ={time.time() - start_time}")
        return copy_one_hop_graph_data(one_hop, "s")

    def convert_spo_to_one_graph(self, table: TableData) -> Dict[str, OneHopGraphData]:
        cached_map = {}
        s_index = -1
        p_index = -1
        o_index = -1
        # format header s, p
        for i in range(len(table.header)):
            if table.header[i] == "s":
                s_index = i
            elif table.header[i] == "p":
                p_index = i
            elif table.header[i] == "o":
                o_index = i
        if s_index == -1 or o_index == -1 or p_index == -1:
            raise RuntimeError(
                f"header must contains column 's','p','o', output={table.data}"
            )
        for row in table.data:
            s_entity = self.convert_raw_data_to_node(
                row[s_index], enable_cache=True, cached_map=cached_map
            )
            o_entity = self.convert_raw_data_to_node(
                row[o_index], enable_cache=False, cached_map=cached_map
            )
            rel = self.convert_raw_data_to_rel(row[p_index], s_entity, o_entity)
            s_one_hop: OneHopGraphData = self._get_cached_one_hop_graph(
                s_entity.biz_id, s_entity.type, cached_map
            )
            if rel.from_entity == s_entity:
                update_cached_one_hop_rel(s_one_hop.out_relations, rel)
            else:
                update_cached_one_hop_rel(s_one_hop.in_relations, rel)

        return cached_map

    def execute_dsl(self, dsl: str, **kwargs) -> TableData:
        if self.rc is None:
            logger.warning(f"{dsl} current is None")
            return TableData()
        res = self.rc.syn_execute(dsl_content=dsl, **kwargs)
        task_resp: ReasonTask = res.task
        if task_resp is None or task_resp.status != "FINISH":
            logger.debug(f"execute dsl failed! {res}")
            return TableData()
        detail = task_resp.result_table_result
        return TableData.from_dict({"header": detail.header, "data": detail.rows})

    def calculate_pagerank_scores(
        self, target_vertex_type, start_nodes: List[Dict], top_k=10
    ) -> Dict:
        if self.gr is None:
            return {}
        target_vertex_type_with_prefix = self.schema.get_label_within_prefix(
            target_vertex_type
        )
        return self.gr.calculate_pagerank_scores(
            target_vertex_type_with_prefix, start_nodes
        )

    def get_entity_prop_by_id(self, biz_id, label) -> Dict:
        if self.rc is None:
            return {}
        return self.rc.query_node(label=label, id_value=biz_id)


if __name__ == "__main__":
    rc = ReasonerClient(
        host_addr="http://antspg-gz00b-006003038079.sa128-sqa.alipay.net:8887",
        project_id=6400004,
    )
    rc.get_reason_schema()
    graph_api = OpenSPGGraphApi(
        project_id="6400004",
        host_addr="http://antspg-gz00b-006003038079.sa128-sqa.alipay.net:8887",
    )
    entity = SPOEntity()
    entity.id_set.append("周杰伦")
    entity.type_set.append(TypeInfo("Person"))
    datas: List[EntityData] = graph_api.get_entity(entity)
    assert len(datas) == 1
    assert datas[0].biz_id == "周杰伦"
    one_hop = graph_api.get_entity_one_hop(datas[0])
    assert one_hop is not None
    # cached
    one_hop = graph_api.get_entity_one_hop(datas[0])
    assert one_hop is not None
