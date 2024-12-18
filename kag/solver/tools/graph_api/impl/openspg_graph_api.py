import logging
from abc import ABC
from typing import List, Dict

from kag.solver.logic.core_modules.config import LogicFormConfiguration
from knext.reasoner.rest.models.reason_task import ReasonTask

from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, OneHopGraphData, Prop, RelationData, \
    copy_one_hop_graph_data
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_biz_id_with_type
from kag.solver.tools.graph_api.graph_api_abc import GraphApiABC
from kag.solver.tools.graph_api.model.table_model import TableData
from knext.reasoner.client import ReasonerClient

logger = logging.getLogger()


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
        logger.warning(f"_convert_edge_to_json failed {p_str}, {e}", exc_info=True)
        return {}
    prop = dict(p)
    prop["original_src_id1__"] = p["__from_id__"]
    prop["original_dst_id2__"] = p["__to_id__"]
    return {"type": p["__label__"], "propertyValues": prop}


def convert_node_to_json(node_str):
    try:
        import json
        node = json.loads(node_str)
    except Exception as e:
        logger.warning(f"_convert_node_to_json failed {node_str}, {e}", exc_info=True)
        return {}
    return {
        "id": node["id"],
        "type": node["__label__"],
        "propertyValues": dict(node),
    }


@GraphApiABC.register("openspg", as_default=True)
class OpenSPGGraphApi(GraphApiABC):
    def __init__(self, project_id: str, host_addr: str, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id
        self.schema: SchemaUtils = SchemaUtils(LogicFormConfiguration({
            "project_id": project_id,
            "host_addr": host_addr
        }))
        self.host_addr = host_addr

        self.rc = ReasonerClient(self.config.host_addr, int(self.project_id))

        self.cache_one_hop_graph: [str, OneHopGraphData] = {}

    def _get_cached_one_hop_graph(self, s_biz_id, s_type_name, cached_map: dict):
        s_biz_id_with_type_name = generate_biz_id_with_type(
            s_biz_id, s_type_name
        )
        return cached_map.get(s_biz_id_with_type_name, None)

    def _put_one_hop_graph_cache(self, one_hop: OneHopGraphData, cached_map: dict):
        s_biz_id_with_type_name = generate_biz_id_with_type(
            one_hop.s.biz_id, one_hop.s.type
        )
        cached_map[s_biz_id_with_type_name] = one_hop

    def _get_node_type_zh(self, s_type_name):
        s_type_without_prefix = self.schema.get_label_without_prefix(s_type_name)
        return self.schema.node_en_zh.get(s_type_without_prefix, s_type_without_prefix)

    def _convert_json_to_entity(self, s_json: dict, enable_cache: bool, cached_map: dict) -> EntityData:
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
            one_hop = OneHopGraphData(None, "")
            one_hop.s = s_entity
            if enable_cache:
                self._put_one_hop_graph_cache(one_hop, cached_map)
        return s_entity

    def _convert_json_to_rel(self, p_json: dict, start_node: EntityData, end_node: EntityData) -> RelationData:
        p_total_type_name = p_json["type"]
        s_type = start_node.type
        o_type = end_node.type
        if len(s_type) > len(o_type):
            p_type = (
                p_json["type"].replace(s_type, "").replace(o_type, "").replace("_", "")
            )
        else:
            p_type = (
                p_json["type"].replace(o_type, "").replace(s_type, "").replace("_", "")
            )
        p_info = {}
        from_id = None
        to_id = None
        for property_key in p_json["propertyValues"].keys():
            if property_key == "original_src_id1__":
                from_id = p_json["propertyValues"][property_key]
            elif property_key == "original_dst_id2__":
                to_id = p_json["propertyValues"][property_key]
            else:
                p_info[property_key] = p_json["propertyValues"][property_key]
        if from_id is None or to_id is None:
            return None
        """
        rel.from_id = json_dict["__from_id__"]
        rel.from_type = json_dict["__from_id_type__"]
        rel.end_id = json_dict["__to_id__"]
        rel.end_type = json_dict["__to_id_type__"]
        rel.type = json_dict["__label__"]
        """
        if s_type in p_total_type_name and s_type != o_type:
            is_out_edge = p_total_type_name.startswith(s_type)
        else:
            is_out_edge = from_id == start_node.biz_id

        if is_out_edge:
            p_info.update(
                {
                    "__label__": p_type,
                    "__from_id__": start_node.biz_id,
                    "__from_id_type__": s_type,
                    "__to_id__": end_node.biz_id,
                    "__to_id_type__": o_type,
                }
            )
        else:
            p_info.update(
                {
                    "__label__": p_type,
                    "__from_id__": end_node.biz_id,
                    "__from_id_type__": o_type,
                    "__to_id__": start_node.biz_id,
                    "__to_id_type__": s_type,
                }
            )

        rel = RelationData.from_dict(p_json, self.schema)
        rel.from_entity = start_node if is_out_edge else end_node
        rel.end_entity = end_node if is_out_edge else start_node
        return rel

    def convert_raw_data_to_node(self, data: str, enable_cache, cached_map) -> EntityData:
        data_json = convert_node_to_json(data)
        return self._convert_json_to_entity(data_json, enable_cache, cached_map)

    def convert_raw_data_to_rel(self, data: str, start_node: EntityData, end_node: EntityData) -> RelationData:
        return self._convert_json_to_rel(convert_edge_to_json(data), start_node, end_node)

    def get_entity(self, entity: SPOEntity) -> List[EntityData]:
        entity_type_list = entity.get_entity_type_set()
        entity_type_list_with_prefix = []
        for entity_type in entity_type_list:
            entity_type_list_with_prefix.append(f"`{self.schema.get_label_within_prefix(entity_type)}`")
        entity_labels = '|'.join(entity_type_list_with_prefix)
        id_set = []
        for entity_id in entity.id_set:
            id_set.append(f'"{entity_id}"')
        id_sets = ",".join(id_set)
        dsl_query = f"""
        MATCH (n:{entity_labels})
        WHERE n.id in ['{id_sets}']
        )
        RETURN n
        """
        tables: TableData = self.execute_dsl(dsl_query)
        return [self.convert_raw_data_to_node(row[0]) for row in tables.data]

    def get_entity_one_hop(self, entity: EntityData) -> OneHopGraphData:
        id = f'"{entity.biz_id}"'
        dsl_query = f"""
        MATCH (s:`{entity.type}`)-[p:rdf_expand()]-(o:Entity)
        WHERE s.id in ['{id}']
        )
        RETURN s,p,o
        """
        one_hop: OneHopGraphData = self._get_cached_one_hop_graph(entity.biz_id, entity.type, self.cache_one_hop_graph)
        if not one_hop:
            table: TableData = self.execute_dsl(dsl_query)
            cached_map = self.convert_spo_to_one_graph(table)
            self.cache_one_hop_graph.update(cached_map)
            one_hop = self._get_cached_one_hop_graph(entity.biz_id, entity.type, self.cache_one_hop_graph)
        if one_hop is None:
            return None
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
            raise RuntimeError(f"header must contains column 's','p','o'")
        for row in table.data:
            s_entity = self.convert_raw_data_to_node(row[s_index], enable_cache=True, cached_map=cached_map)
            o_entity = self.convert_raw_data_to_node(row[o_index], enable_cache=False, cached_map=cached_map)
            rel = self.convert_raw_data_to_rel(row[p_index], s_entity, o_entity)
            s_one_hop: OneHopGraphData = self._get_cached_one_hop_graph(s_entity.biz_id, s_entity.type, cached_map)
            if rel.from_entity == s_entity:
                update_cached_one_hop_rel(s_one_hop.out_relations, rel)
            else:
                update_cached_one_hop_rel(s_one_hop.in_relations, rel)

        return cached_map

    def execute_dsl(self, dsl: str) -> TableData:
        res = self.rc.syn_execute(dsl_content=dsl)
        task_resp: ReasonTask = res.task
        if task_resp is None or task_resp.status != "FINISH":
            logger.warning(f"execute dsl failed! {res}")
            return TableData()
        detail = task_resp.result_table_result
        return TableData.from_dict({
            "header": detail.header,
            "data": detail.rows
        })


if __name__ == "__main__":
    graph_api = OpenSPGGraphApi(project_id="4", host_addr="http://127.0.0.1:8887")
    entity = SPOEntity()
    entity.id_set.append("确认是否可认定为事实劳动关系")
    entity.type_set.append("Pillar")
    datas: List[EntityData] = graph_api.get_entity(entity)
    assert len(datas) == 1
    assert datas[0].biz_id == "确认是否可认定为事实劳动关系"
    one_hop = graph_api.get_entity_one_hop(datas[0])
    assert one_hop is not None
