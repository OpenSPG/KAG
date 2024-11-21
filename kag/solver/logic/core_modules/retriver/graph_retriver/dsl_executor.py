import concurrent.futures
import itertools
import logging
import time
from typing import List

from knext.reasoner import TableResult, ReasonTask
from knext.reasoner.client import ReasonerClient
from kag.solver.logic.core_modules.common.one_hop_graph import copy_one_hop_graph_data, EntityData, Prop, \
    OneHopGraphData, RelationData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.utils import generate_biz_id_with_type
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode

logger = logging.getLogger()


class DslRunner:
    def __init__(self, project_id: str, schema: SchemaUtils, config: LogicFormConfiguration):
        # Initialize the DslRunner with project ID, schema, and configuration.
        """
        Initialize the DslRunner for graph database access using Cypher or other languages to retrieve results as OneHopGraph.

        :param project_id: A string representing the ID of the project.
        :param schema: An object of type Schema used for defining the structure of the graph data.
        :param config: An instance of LogicFormConfiguration containing configuration settings.
        """
        self.project_id = project_id
        self.schema = schema
        self.config = config
        self.rc = ReasonerClient(self.config.host_addr, int(self.project_id))

    def get_cached_one_hop_data(self, query_one_graph_cache: dict, biz_id, spo_name):
        if biz_id in query_one_graph_cache.keys():
            return copy_one_hop_graph_data(query_one_graph_cache[biz_id], spo_name)
        return None

    def call_sub_event(self, s_biz_id_set: list, s_node_type: str, o_node_type: str, p_name: str, out_direct: bool,
                       filter_map: dict = None):
        pass

    def run_dsl(self, query, dsl, start_id, params, schema: SchemaUtils, graph_output=False):
        pass

    """
        batch query with s and o
    """

    def query_vertex_one_graph_by_s_o_ids(self, s_node_set: List[EntityData], o_node_set: List[EntityData],
                                          cached_map: dict,n: GetSPONode=None):
        pass

    """
        batch query with s, only get property
    """

    def query_vertex_property_by_s_ids(self, s_biz_id_set: list, s_node_type: str, cached_map: dict):
        pass


class DslRunnerOnGraphStore(DslRunner):

    def __init__(self, project_id, schema: SchemaUtils, config: LogicFormConfiguration):
        super().__init__(project_id, schema, config)
        self.schema = schema

    def run_dsl(self, query, dsl, start_id, params, schema: SchemaUtils, graph_output=False):
        pass

    def _get_filter_gql(self, filter_map: dict, alias: str):
        if filter_map is None or alias not in filter_map:
            return None
        return filter_map[alias]

    def _convert_node_to_json(self, node_str):
        try:
            import json
            node = json.loads(node_str)
        except:
            return {}
        return {
            'id': node['id'],
            'type': node['__label__'],
            'propertyValues': dict(node)
        }

    def _convert_edge_to_json(self, p_str):
        try:
            import json
            p = json.loads(p_str)
        except:
            return {}
        prop = dict(p)
        prop['original_src_id1__'] = p['__from_id__']
        prop['original_dst_id2__'] = p['__to_id__']
        return {
            'type': p['__label__'],
            'propertyValues': prop
        }

    def replace_qota(self, s: str):
        return s.replace("'", "\\'")

    def _generate_gql_type(self, biz_set: list, node_type: str):
        if biz_set is None or len(biz_set) == 0 or node_type is None:
            return ":Entity"
        return f":{node_type}"
    """
        batch query with s and o
    """

    def _do_query_vertex_one_graph_by_s_o_ids(self, s_biz_id: list, s_node_type: str, o_biz_id: list, o_node_type: str,
                                              p_name: str = None, filter_map: dict = None):

        s_biz_id_set = [f'"{self.replace_qota(str(s_id))}"' for s_id in s_biz_id]

        o_biz_id_set = []
        if o_biz_id is not None:
            o_biz_id_set = [f"'{self.replace_qota(str(o_id))}'" for o_id in o_biz_id]

        s_where_cluase = None
        return_cluase = ["p"]
        return_cluase.append("s.id as s_id")
        return_cluase.append("o.id as o_id")

        return_cluase.append("s")

        s_where_filter_cluase = self._get_filter_gql(filter_map, "s")
        if s_where_filter_cluase is not None:
            s_where_cluase = f"{s_where_filter_cluase}"

        o_where_cluase = None

        o_where_filter_cluase = self._get_filter_gql(filter_map, "o")
        if o_where_filter_cluase is not None:
            o_where_cluase = f"{o_where_filter_cluase}"
        return_cluase.append("o")

        p_where_cluase = self._get_filter_gql(filter_map, "p")

        s_gql = f"(s{self._generate_gql_type(s_biz_id_set, s_node_type)})"
        o_gql = f"(o{self._generate_gql_type(o_biz_id_set, o_node_type)})"
        where_cluase = []
        if s_where_cluase:
            where_cluase.append(s_where_cluase)

        if o_where_cluase:
            where_cluase.append(o_where_cluase)

        if p_where_cluase:
            where_cluase.append(p_where_cluase)
        gql_param = {
            "start_alias": "s" if len(s_biz_id_set) > 0 else "o",
            "s_type": s_node_type,
            "o_type": o_node_type
        }
        if len(s_biz_id_set) > 0:
            where_cluase.append(f"s.id in $sid")
            gql_param["sid"] = f'[{",".join(s_biz_id_set)}]'

        if len(o_biz_id_set) > 0:
            where_cluase.append(f"o.id in $oid")
            gql_param["oid"] = f'[{",".join(o_biz_id_set)}]'
        if p_name is None:
            p_name = "rdf_expand()"
        gql_set = self._generate_gql_prio_set(s_node_type, s_biz_id_set, o_node_type, o_biz_id_set, p_name, where_cluase, return_cluase)
        logger.debug("query_vertex_one_graph_by_s_o_ids query " + str(gql_set))

        start_time = time.time()
        for gql in gql_set:
            res = self.rc.syn_execute(gql, **gql_param)
            add_alias = []
            if len(s_biz_id_set) > 0:
                add_alias.append("s")
            if len(o_biz_id_set) > 0:
                add_alias.append("o")
            out = self.parse_one_hot_graph_graph_detail_with_id_map(res.task, add_alias)
            logger.debug(f"query_vertex_one_graph_by_s_o_ids {s_biz_id_set} cost end time {time.time() - start_time}")
            if out is not None and len(out) > 0:
                return out
        return {}

    def _generate_gql_prio_set(self, s_type, s_biz_id_set, o_type, o_biz_id_set, p_type, where_cluase, return_cluase):
        s_gql = f"(s{self._generate_gql_type(s_biz_id_set, s_type)})"
        o_gql = f"(o{self._generate_gql_type(o_biz_id_set, o_type)})"
        rdf_expand_gql = f"""match {s_gql}-[p:rdf_expand()]-{o_gql}
        {'where ' + "and".join(where_cluase) if len(where_cluase) > 0 else ''}
        return {','.join(return_cluase)}"""
        if p_type == "rdf_expand()":
            return [rdf_expand_gql]
        s_without_prefix_type = self.schema.get_label_without_prefix(s_type)
        o_without_prefix_type = self.schema.get_label_without_prefix(o_type)
        ret_gql = []
        if (s_without_prefix_type, o_without_prefix_type) in self.schema.so_p_en and p_type in self.schema.so_p_en[(s_without_prefix_type, o_without_prefix_type)]:
            ret_gql.append(f"""match (s:{s_type})-[p:{p_type}]->(o:{o_type})
        {'where ' + "and".join(where_cluase) if len(where_cluase) > 0 else ''}
        return {','.join(return_cluase)}""")
        if (o_without_prefix_type, s_without_prefix_type) in self.schema.op_s_en  and p_type in self.schema.op_s_en[(o_without_prefix_type, s_without_prefix_type)]:
            ret_gql.append(f"""match (s:{s_type})<-[p:{p_type}]-(o:{o_type})
                    {'where ' + "and".join(where_cluase) if len(where_cluase) > 0 else ''}
                    return {','.join(return_cluase)}""")
        ret_gql.append(rdf_expand_gql)
        return ret_gql

    def _cartesian_product_with_default(self, list1, list2, default=None):
        # 如果任何一个列表为空，使用包含默认值的列表替代
        list1 = list1 if list1 else [default]
        list2 = list2 if list2 else [default]

        return list(itertools.product(list1, list2))

    def _get_node_type_zh(self, node_type):
        if node_type == "attribute":
            return "文本"
        return node_type
    def _get_p_type_name(self, n: GetSPONode):
        if n is None:
            return None
        return n.p.get_entity_first_type()
    def _get_entity_type_name(self, d: EntityData, n: GetSPONode=None, alias=None):
        if d is None and n is None:
            return None
        return self.schema.get_label_within_prefix(n.s.get_entity_first_type() if alias=="s" else n.o.get_entity_first_type()) if d is None else d.type

    def query_vertex_one_graph_by_s_o_ids(self, s_node_set: List[EntityData], o_node_set: List[EntityData],
                                          cached_map: dict, n: GetSPONode=None):
        one_hop_graph_map = {}
        is_enable_cache = True
        if (len(s_node_set) != 0 and len(o_node_set) != 0) or self._get_p_type_name(n):
            # do not cache
            is_enable_cache = False
        s_uncached_biz_id = []
        o_uncached_biz_id = []
        if is_enable_cache:
            for s_node in s_node_set:
                cached_id = generate_biz_id_with_type(s_node.biz_id, self._get_node_type_zh(s_node.type_zh if s_node.type_zh else s_node.type))
                cached_graph = self.get_cached_one_hop_data(cached_map, cached_id, "s")
                if cached_graph:
                    one_hop_graph_map[cached_id] = cached_graph
                else:
                    s_uncached_biz_id.append(s_node)

            for o_node in o_node_set:
                cached_id = generate_biz_id_with_type(o_node.biz_id, self._get_node_type_zh(o_node.type_zh if o_node.type_zh else o_node.type))
                cached_graph = self.get_cached_one_hop_data(cached_map, cached_id, "o")
                if cached_graph:
                    one_hop_graph_map[cached_id] = cached_graph
                else:
                    o_uncached_biz_id.append(o_node)
            if len(s_uncached_biz_id) == 0 and len(o_uncached_biz_id) == 0:
                return one_hop_graph_map
        else:
            s_uncached_biz_id = s_node_set
            o_uncached_biz_id = o_node_set

        combined_list = self._shuffle_query_node(s_uncached_biz_id, o_uncached_biz_id)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._do_query_vertex_one_graph_by_s_o_ids, [] if s_node is None else [s_node.biz_id],
                                self._get_entity_type_name(s_node, n, "s"), [] if o_node is None else [o_node.biz_id],
                                self._get_entity_type_name(o_node, n, "o"), self._get_p_type_name(n)) for
                s_node, o_node in
                combined_list]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            for r in results:
                one_hop_graph_map.update(r)
        for node in s_uncached_biz_id + o_uncached_biz_id:
            cached_id = generate_biz_id_with_type(node.biz_id, self._get_node_type_zh(node.type_zh if node.type_zh else node.type))
            if cached_id not in one_hop_graph_map:
                continue
            one_hop_graph = one_hop_graph_map[cached_id]
            one_hop_graph.s.score = node.score
        # updated score
        return one_hop_graph_map

    def _shuffle_query_node(self, s_nodes: List[EntityData], o_nodes: List[EntityData]):
        s_group_types = self._extra_node_id_group_by_type(s_nodes)
        o_group_types = self._extra_node_id_group_by_type(o_nodes)
        combined_list = self._cartesian_product_with_default(s_group_types, o_group_types)
        node_ids = []
        for s_group, o_group in combined_list:
            node_ids = node_ids + self._cartesian_product_with_default(s_group, o_group)
        return node_ids

    def _extra_node_id_group_by_type(self, nodes: List[EntityData]):
        type_map = {}
        for node in nodes:
            if node.type not in type_map:
                type_map[node.type] = []
            type_map[node.type].append(node)
        return list(type_map.values())

    def query_vertex_property_by_s_ids(self, s_biz_id_set: list, s_node_type: str, cached_map: dict):
        one_hop_graph_dict = {}
        s_uncached_biz_id_set = []
        s_node_type_zh = self._get_node_type_zh(s_node_type)
        for s_id in s_biz_id_set:
            cache_id_with_type = generate_biz_id_with_type(s_id, s_node_type_zh)
            cached_graph = self.get_cached_one_hop_data(cached_map, cache_id_with_type, "s")
            if cached_graph:
                one_hop_graph_dict[cache_id_with_type] = cached_graph
            else:
                s_uncached_biz_id_set.append(s_id)
        if len(s_uncached_biz_id_set) == 0:
            return one_hop_graph_dict

        s_biz_id_set = s_uncached_biz_id_set
        s_biz_id_set = [f"'{self.replace_qota(str(s_id))}'" for s_id in s_biz_id_set]

        return_cluase = []
        id_rep = "id"

        gql_param = {
            "start_alias": "s"
        }
        if len(s_biz_id_set) > 0:
            s_where_cluase = "s.id in $sid"
            gql_param["sid"] = f"[{','.join(s_biz_id_set)}]"
        else:
            return {}

        return_cluase.append("s")
        return_cluase.append("s.id as s_id")

        gql = f"""
        match (s{':' + 'Entity' if len(s_biz_id_set) != 0 else ''}{' where ' + s_where_cluase if s_where_cluase else ''})
        return {','.join(return_cluase)}
        """
        logger.debug("query_vertex_one_graph_by_s_o_ids query " + gql)
        start_time = time.time()

        res = self.rc.syn_execute(gql, **gql_param)
        add_alias = []
        if len(s_biz_id_set) > 0:
            add_alias.append("s")
        out = self.parse_one_hot_graph_graph_detail_with_id_map(res.task, add_alias)
        one_hop_graph_dict.update(out)
        logger.debug(f"query_vertex_one_graph_by_s_o_ids {s_biz_id_set} cost end time {time.time() - start_time}")
        return one_hop_graph_dict

    def _trans_normal_p_json(self, p_json, s_json, o_json):
        s_type = s_json['type']
        s_biz_id = s_json["propertyValues"]["id"]
        o_type = o_json['type']
        o_biz_id = o_json["propertyValues"]["id"]
        p_total_type_name = p_json['type']
        if len(s_type) > len(o_type):
            p_type = p_json['type'].replace(s_type, "").replace(o_type, "").replace("_", "")
        else:
            p_type = p_json['type'].replace(o_type, "").replace(s_type, "").replace("_", "")
        p_info = {}
        from_id = None
        to_id = None
        for property_key in p_json['propertyValues'].keys():
            if property_key == "original_src_id1__":
                from_id = p_json['propertyValues'][property_key]
            elif property_key == "original_dst_id2__":
                to_id = p_json['propertyValues'][property_key]
            else:
                p_info[property_key] = p_json['propertyValues'][property_key]
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
            is_out_edge = from_id == s_biz_id

        if is_out_edge:
            p_info.update({
                "__label__": p_type,
                "__from_id__": s_biz_id,
                "__from_id_type__": s_type,
                "__to_id__": o_biz_id,
                "__to_id_type__": o_type
            })
        else:
            p_info.update({
                "__label__": p_type,
                "__from_id__": o_biz_id,
                "__from_id_type__": o_type,
                "__to_id__": s_biz_id,
                "__to_id_type__": s_type
            })

        return p_info

    def _check_need_property(self, json_data):
        if "propertyValues" not in json_data.keys():
            return False
        if "type" not in json_data.keys():
            return False
        if "id" not in json_data.keys():
            return False
        if "id" not in json_data["propertyValues"].keys():
            return False
        return True

    def parse_one_hot_graph_graph_detail_with_id_map(self, task_resp: ReasonTask, add_alias: list):
        one_hop_graph_map = {}
        if task_resp is None or task_resp.status != "FINISH":
            return one_hop_graph_map
        detail = task_resp.result_table_result
        if detail.total == 0:
            return one_hop_graph_map
        tmp_graph_parse_result_map = {}
        s_index = -1
        p_index = -1
        o_index = -1
        # format header s, p
        for i in range(len(detail.header)):
            if detail.header[i] == "s":
                s_index = i
            elif detail.header[i] == "p":
                p_index = i
            elif detail.header[i] == "o":
                o_index = i
        if p_index is None:
            return one_hop_graph_map

        # get all EntityData first
        for data in detail.rows:
            s_entity = None
            o_entity = None
            s_json = {}
            if s_index != -1:
                s_json = self._convert_node_to_json(data[s_index])
                if self._check_need_property(s_json) is False:
                    continue
                prop_values = s_json['propertyValues']
                s_biz_id = prop_values["id"]
                s_type_name = s_json["type"]
                s_biz_id_with_type_name = generate_biz_id_with_type(s_biz_id, self._get_node_type_zh(s_type_name))
                if s_biz_id_with_type_name not in tmp_graph_parse_result_map.keys():
                    s_entity = EntityData()
                    s_entity.type = s_type_name
                    s_entity.type_zh = self._get_node_type_zh(s_type_name)
                    s_entity.prop = Prop.from_dict(prop_values, s_entity.type, None)
                    s_entity.biz_id = s_biz_id
                    s_entity.name = prop_values.get("name", "")
                    if "description" in prop_values.keys():
                        s_entity.description = prop_values["description"]
                    one_hop_graph = OneHopGraphData(None, "s")
                    one_hop_graph.s = s_entity
                    tmp_graph_parse_result_map[s_biz_id_with_type_name] = one_hop_graph
                else:
                    s_entity = tmp_graph_parse_result_map[s_biz_id_with_type_name].s

                if "s" in add_alias and s_biz_id_with_type_name not in one_hop_graph_map.keys():
                    one_hop_graph_map[s_biz_id_with_type_name] = tmp_graph_parse_result_map[s_biz_id_with_type_name]
            else:
                s_biz_id_with_type_name = None

            if o_index == -1 or p_index == -1:
                continue

            o_json = {}
            if o_index != -1:
                o_json = self._convert_node_to_json(data[o_index])
                if self._check_need_property(o_json) is False:
                    continue
                prop_values = o_json['propertyValues']
                o_biz_id = prop_values["id"]
                o_type_name = o_json["type"]
                o_biz_id_with_type_name = generate_biz_id_with_type(o_biz_id, self._get_node_type_zh(o_type_name))
                if o_biz_id_with_type_name not in tmp_graph_parse_result_map.keys():
                    o_entity = EntityData()
                    o_entity.type = o_type_name
                    o_entity.type_zh = self._get_node_type_zh(o_type_name)
                    o_entity.prop = Prop.from_dict(prop_values, o_entity.type, None)
                    o_entity.biz_id = o_biz_id

                    o_entity.name = prop_values.get("name", "")
                    if "description" in o_json.keys():
                        o_entity.description = o_json["description"]
                    one_hop_graph = OneHopGraphData(None, "o")
                    one_hop_graph.s = o_entity
                    tmp_graph_parse_result_map[o_biz_id_with_type_name] = one_hop_graph
                else:
                    o_entity = tmp_graph_parse_result_map[o_biz_id_with_type_name].s

                if "o" in add_alias and o_biz_id_with_type_name not in one_hop_graph_map.keys():
                    one_hop_graph_map[o_biz_id_with_type_name] = tmp_graph_parse_result_map[o_biz_id_with_type_name]
            else:
                o_biz_id_with_type_name = None

            if s_entity is None and o_entity is None:
                logger.info("parse_one_hot_graph_graph_detail_with_id_map entity is None")
                continue

            if p_index == -1:
                continue
            p_json = self._convert_edge_to_json(data[p_index])
            p_json = self._trans_normal_p_json(p_json, s_json, o_json)
            rel = RelationData.from_dict(p_json, None)
            # if rel.type in ['similarity', 'source']:
            #     continue
            if s_entity is None:
                s_entity = EntityData()
                if rel.from_id == o_entity.biz_id:
                    s_entity.biz_id = rel.end_id
                    s_entity.type = rel.end_type
                    s_entity.type_zh = self._get_node_type_zh(rel.end_type)
                else:
                    s_entity.biz_id = rel.from_id
                    s_entity.type = rel.from_type
                    s_entity.type_zh = self._get_node_type_zh(rel.from_type)

            if o_entity is None:
                o_entity = EntityData()
                if rel.from_id == s_entity.biz_id:
                    o_entity.biz_id = rel.end_id
                    o_entity.type = rel.end_type
                    o_entity.type_zh = self._get_node_type_zh(rel.end_type)
                else:
                    o_entity.biz_id = rel.from_id
                    o_entity.type = rel.from_type
                    o_entity.type_zh = self._get_node_type_zh(rel.from_type)

            if generate_biz_id_with_type(rel.from_id, rel.from_type) == generate_biz_id_with_type(s_entity.biz_id,
                                                                                                  s_type_name):
                rel.from_entity = s_entity
                rel.end_entity = o_entity

                if s_biz_id_with_type_name is not None and s_biz_id_with_type_name in tmp_graph_parse_result_map.keys():
                    if rel.type in tmp_graph_parse_result_map[s_biz_id_with_type_name].out_relations.keys():
                        tmp_graph_parse_result_map[s_biz_id_with_type_name].out_relations[rel.type].append(rel)
                    else:
                        tmp_graph_parse_result_map[s_biz_id_with_type_name].out_relations[rel.type] = [rel]
                if o_biz_id_with_type_name is not None and o_biz_id_with_type_name in tmp_graph_parse_result_map.keys():
                    if rel.type in tmp_graph_parse_result_map[o_biz_id_with_type_name].in_relations.keys():
                        tmp_graph_parse_result_map[o_biz_id_with_type_name].in_relations[rel.type].append(rel)
                    else:
                        tmp_graph_parse_result_map[o_biz_id_with_type_name].in_relations[rel.type] = [rel]
            else:
                rel.from_entity = o_entity
                rel.from_alias = "o"
                rel.end_entity = s_entity
                rel.end_alias = "s"
                if s_biz_id_with_type_name is not None and s_biz_id_with_type_name in tmp_graph_parse_result_map.keys():
                    if rel.type in tmp_graph_parse_result_map[s_biz_id_with_type_name].in_relations.keys():
                        tmp_graph_parse_result_map[s_biz_id_with_type_name].in_relations[rel.type].append(rel)
                    else:
                        tmp_graph_parse_result_map[s_biz_id_with_type_name].in_relations[rel.type] = [rel]

                if o_biz_id_with_type_name is not None and o_biz_id_with_type_name in tmp_graph_parse_result_map.keys():
                    if rel.type in tmp_graph_parse_result_map[o_biz_id_with_type_name].out_relations.keys():
                        tmp_graph_parse_result_map[o_biz_id_with_type_name].out_relations[rel.type].append(rel)
                    else:
                        tmp_graph_parse_result_map[o_biz_id_with_type_name].out_relations[rel.type] = [rel]
        return one_hop_graph_map
