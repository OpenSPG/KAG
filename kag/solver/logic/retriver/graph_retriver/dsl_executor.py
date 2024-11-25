import logging
import itertools
import time
import concurrent.futures

from kag.solver.logic.common.one_hop_graph import copy_one_hop_graph_data, EntityData, Prop, \
    OneHopGraphData, RelationData
from kag.solver.logic.common.schema import Schema
from kag.solver.logic.common.utils import generate_biz_id_with_type
from kag.solver.logic.config import LogicFormConfiguration
from kag.common.graphstore.graph_store import GraphStore

logger = logging.getLogger()

class DslRunner:
    def __init__(self, project_id: str, schema: Schema, config: LogicFormConfiguration):
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
        self.enable_subgraph_direct = self.config.enabled_subgraph_direct

    def get_cached_one_hop_data(self, query_one_graph_cache:dict, biz_id, spo_name):
        if biz_id in query_one_graph_cache.keys():
            return copy_one_hop_graph_data(query_one_graph_cache[biz_id], spo_name)
        return None

    def call_sub_event(self, s_biz_id_set: list, s_node_type: str, o_node_type: str, p_name: str, out_direct: bool,
                       filter_map: dict = None):
        pass

    def run_dsl(self, query, dsl, start_id, params, schema: Schema, graph_output= False):
        pass
    """
        batch query with s and o
    """
    def query_vertex_one_graph_by_s_o_ids(self, s_biz_id: list, s_node_type: str, o_biz_id: list, o_node_type: str, cached_map: dict):
        pass
    """
        batch query with s, only get property
    """
    def query_vertex_property_by_s_ids(self, s_biz_id_set: list, s_node_type: str, cached_map: dict):
        pass


class DslRunnerOnGraphStore(DslRunner):


    def __init__(self, project_id: str, schema: Schema, config: LogicFormConfiguration, graph_store: GraphStore):
        super().__init__(project_id, schema, config)
        self.graph_store: GraphStore = graph_store
        self.schema = schema


    def trans_schema_to_geabase_label(self, node_type: str):
        node_type = node_type.lower()
        return node_type.replace(".", "_")

    def _get_enable_direct(self, label):
        if not self.enable_subgraph_direct:
            return False
        if label in ['Hospital']:
            return True
        return False

    def run_dsl(self, query, dsl, start_id, params, schema: Schema, graph_output=False):
        pass

    def _get_filter_gql(self, filter_map: dict, alias: str):
        if filter_map is None or alias not in filter_map:
            return None
        return filter_map[alias]

    def _convert_node_to_json(self, node):
        return {
            'id': node.element_id,
            'type': list(node.labels)[0],
            'propertyValues': dict(node)
        }

    def _convert_edge_to_json(self, p):
        prop = dict(p)
        start_node = self._convert_node_to_json(p.start_node)
        end_node = self._convert_node_to_json(p.end_node)
        prop['original_src_id1__'] = start_node['propertyValues']['id']
        prop['original_dst_id2__'] = end_node['propertyValues']['id']
        return {
            'type': p.type,
            'propertyValues': prop
        }

    def replace_qota(self, s: str):
        return s.replace("'", "\\'")
    """
        batch query with s and o
    """
    def _do_query_vertex_one_graph_by_s_o_ids(self, s_biz_id: list, s_node_type: str, o_biz_id: list, o_node_type: str, p_name: str = None, filter_map: dict = None):

        s_biz_id_set = [f"'{self.replace_qota(str(s_id))}'" for s_id in s_biz_id]

        o_biz_id_set = []
        if o_biz_id is not None:
            o_biz_id_set = [f"'{self.replace_qota(str(o_id))}'" for o_id in o_biz_id]

        s_where_cluase = None
        return_cluase = ["p"]
        id_rep = "id"

        if len(s_biz_id_set) > 1:
            s_where_cluase = f"s.{id_rep} in [{','.join(s_biz_id_set)}]"
        elif len(s_biz_id_set) == 1:
            s_where_cluase = f"s.{id_rep} = {s_biz_id_set[0]}"
        return_cluase.append("s")

        s_where_filter_cluase = self._get_filter_gql(filter_map, "s")
        if s_where_filter_cluase is not None:
            s_where_cluase = f"{s_where_cluase + ' and' if s_where_cluase else ''} {s_where_filter_cluase}"

        o_where_cluase = None
        if len(o_biz_id_set) > 1:
            o_where_cluase = f"o.{id_rep} in [{','.join(o_biz_id_set)}]"
        elif len(o_biz_id_set) == 1:
            o_where_cluase = f"o.{id_rep} = {o_biz_id_set[0]}"

        o_where_filter_cluase = self._get_filter_gql(filter_map, "o")
        if o_where_filter_cluase is not None:
            o_where_cluase = f"{o_where_cluase + ' and' if o_where_cluase else ''} {o_where_filter_cluase}"
        return_cluase.append("o")

        p_where_cluase = self._get_filter_gql(filter_map, "p")

        s_gql = f"(s{':' + 'Entity' if len(s_biz_id_set) != 0 else ''}{' where ' + s_where_cluase if s_where_cluase else ''})"
        o_gql = f"(o{':' + 'Entity' if len(o_biz_id_set) != 0 else ''}{' where ' + o_where_cluase if o_where_cluase else ''})"
        if "where" in s_gql:
            gql = f"""
                        match {s_gql}-[p{':'+p_name if p_name is not None else ''} {' where ' + p_where_cluase if p_where_cluase else ''}]{"-" if not self._get_enable_direct(s_node_type) else "->"}{o_gql}
                        return {','.join(return_cluase)} limit 50
                        """
        elif "where" in o_gql:
            gql = f"""
                        match {o_gql}{"-" if not self._get_enable_direct(o_node_type) else "<-"}[p{':'+p_name if p_name is not None else ''} {' where ' + p_where_cluase if p_where_cluase else ''}]-{s_gql}
                        return {','.join(return_cluase)} limit 50
                        """
        else:
            logger.warning(f"query_vertex_one_graph_by_s_o_ids not found id list s_biz_id:{s_biz_id}, o_biz_id:{o_biz_id}")
            return {}
        logger.debug("query_vertex_one_graph_by_s_o_ids query " + gql)
        start_time = time.time()
        res = self.graph_store.run_script(gql)
        add_alias = []
        if len(s_biz_id_set) > 0:
            add_alias.append("s")
        if len(o_biz_id_set) > 0:
            add_alias.append("o")
        out = self.parse_one_hot_graph_graph_detail_with_id_map(res, add_alias)
        logger.debug(f"query_vertex_one_graph_by_s_o_ids {s_biz_id_set} cost end time {time.time() - start_time}")
        return out

    def _cartesian_product_with_default(self, list1, list2, default=None):
        # 如果任何一个列表为空，使用包含默认值的列表替代
        list1 = list1 if list1 else [default]
        list2 = list2 if list2 else [default]

        return list(itertools.product(list1, list2))

    def _get_node_type_zh(self, node_type):
        if node_type == "attribute":
            return "文本"
        return node_type

    def query_vertex_one_graph_by_s_o_ids(self, s_biz_id: list, s_node_type: str, o_biz_id: list, o_node_type: str, cached_map: dict):
        one_hop_graph_map = {}
        is_enable_cache = True
        if len(s_biz_id) != 0 and len(o_biz_id) !=0:
            # do not cache
            is_enable_cache = False
        s_uncached_biz_id = []
        o_uncached_biz_id = []
        if is_enable_cache:
            for s_id in s_biz_id:
                cached_id = generate_biz_id_with_type(s_id, self._get_node_type_zh(s_node_type))
                cached_graph = self.get_cached_one_hop_data(cached_map, cached_id, "s")
                if cached_graph:
                    one_hop_graph_map[cached_id] = cached_graph
                else:
                    s_uncached_biz_id.append(s_id)

            for o_id in o_biz_id:
                cached_id = generate_biz_id_with_type(o_id, self._get_node_type_zh(o_node_type))
                cached_graph = self.get_cached_one_hop_data(cached_map, cached_id, "o")
                if cached_graph:
                    one_hop_graph_map[cached_id] = cached_graph
                else:
                    o_uncached_biz_id.append(o_id)
            if len(s_uncached_biz_id) == 0 and len(o_uncached_biz_id) == 0:
                return one_hop_graph_map
        else:
            s_uncached_biz_id = s_biz_id
            o_uncached_biz_id = o_biz_id

        is_enable_batch_query = True if len(s_uncached_biz_id) > 1 or len(o_uncached_biz_id) > 1 else False
        if is_enable_batch_query:
            # shuffle
            combined_list = self._cartesian_product_with_default(s_uncached_biz_id, o_uncached_biz_id)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._do_query_vertex_one_graph_by_s_o_ids, [] if s_id is None else [s_id], s_node_type, [] if o_id is None else [o_id], o_node_type) for
                           s_id, o_id in
                           combined_list]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                for r in results:
                    one_hop_graph_map.update(r)
            return one_hop_graph_map
        else:
            r = self._do_query_vertex_one_graph_by_s_o_ids(s_uncached_biz_id, s_node_type,
                                                                     o_uncached_biz_id, o_node_type)
            one_hop_graph_map.update(r)
        return one_hop_graph_map

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

        if len(s_biz_id_set) > 1:
            s_where_cluase = f"{id_rep} in [{','.join(s_biz_id_set)}]"
        elif len(s_biz_id_set) == 1:
            s_where_cluase = f"{id_rep} = {s_biz_id_set[0]}"
        else:
            return {}
        return_cluase.append("s")


        gql = f"""
        match (s{':' + 'Entity' if len(s_biz_id_set) != 0 else ''}{' where ' + s_where_cluase if s_where_cluase else ''})
        return {','.join(return_cluase)}
        """
        logger.debug("query_vertex_one_graph_by_s_o_ids query " + gql)
        start_time = time.time()
        res = self.graph_store.run_script(gql)
        add_alias = []
        if len(s_biz_id_set) > 0:
            add_alias.append("s")
        out = self.parse_one_hot_graph_graph_detail_with_id_map(res, add_alias)
        one_hop_graph_dict.update(out)
        logger.debug(f"query_vertex_one_graph_by_s_o_ids {s_biz_id_set} cost end time {time.time() - start_time}")
        return one_hop_graph_dict

    def _trans_normal_p_json(self, p_json, s_json, o_json):
        s_type = s_json['type']
        s_biz_id = s_json["propertyValues"]["id"]
        o_type = o_json['type']
        o_biz_id = o_json["propertyValues"]["id"]
        p_total_type_name = p_json['type']
        p_type = p_json['type'].replace(s_type, "").replace(o_type, "").replace("_", "")
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

    def parse_one_hot_graph_graph_detail_with_id_map(self, detail, add_alias:list):
        one_hop_graph_map = {}
        if detail is None:
            return one_hop_graph_map

        tmp_graph_parse_result_map = {}
        # format header s, p
        s_index = "s"
        p_index = "p"
        o_index = "o"

        # get all EntityData first
        for data in detail:
            s_entity = None
            o_entity = None
            s_json = self._convert_node_to_json(data[s_index])
            if self._check_need_property(s_json) is False:
                continue
            if s_index != -1:
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
                    s_entity.name = prop_values["name"]
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

            o_json = self._convert_node_to_json(data[o_index])
            if self._check_need_property(o_json) is False:
                continue
            if o_index != -1:
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

                    o_entity.name = prop_values["name"]
                    if "description" in o_json.keys():
                        o_entity.description = prop_values["description"]
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

            if generate_biz_id_with_type(rel.from_id, rel.from_type) == generate_biz_id_with_type(s_entity.biz_id, s_type_name):
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
