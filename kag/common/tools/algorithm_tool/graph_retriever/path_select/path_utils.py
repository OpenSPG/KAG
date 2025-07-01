import logging
import time
from typing import List
import concurrent.futures

from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    OneHopGraphData,
)
from kag.common.parser.logic_node_parser import GetSPONode
from kag.common.tools.graph_api.graph_api_abc import (
    generate_gql_id_params,
    generate_label,
)

logger = logging.getLogger()


def extra_relation_candis_types(n: GetSPONode):
    p_type_set = n.p.type_set
    p_label_str_set = []
    p_label_set = []
    for p_type in p_type_set:
        if p_type.std_entity_type is not None:
            p_label_set.append(p_type.std_entity_type)
            p_label_str_set.append(f"`{p_type.std_entity_type}`")
        else:
            p_label_str_set.append(f"`{p_type.un_std_entity_type}`")
    return p_label_str_set


def generate_gql_head_element(alias, entity: List[EntityData]):
    params = {}
    where_gql = []
    e_ids = set(e.biz_id for e in entity)
    if len(e_ids):
        params[f"{alias}_id"] = generate_gql_id_params(list(e_ids))
        where_gql.append(f"{alias}.id in ${alias}_id")
    return params, where_gql


def generate_gql_spo_element(
    n: GetSPONode, heads: List[EntityData], tails: List[EntityData], schema
):
    params = {}
    where_gql = []
    heads_params, head_where_gql = generate_gql_head_element("s", heads)
    params.update(heads_params)
    where_gql.extend(head_where_gql)

    tails_params, tail_where_gql = generate_gql_head_element("o", tails)
    params.update(tails_params)
    where_gql.extend(tail_where_gql)

    header_std_labels = generate_label(n.s, heads, schema)
    gql_header_labels = "|".join(header_std_labels)

    tail_std_labels = generate_label(n.o, tails, schema)
    gql_tail_labels = "|".join(tail_std_labels)

    gql_rel_labels = extra_relation_candis_types(n)

    return gql_header_labels, gql_rel_labels, gql_tail_labels, where_gql, params


def run_gql(graph_api, spg_gql, **kwargs) -> List[OneHopGraphData]:
    try:
        start_time = time.time()
        fat_table = graph_api.execute_dsl(spg_gql, **kwargs)
        logger.info(f"run gql cost {time.time() - start_time}")
        start_time = time.time()
        one_graph_map = graph_api.convert_spo_to_one_graph(fat_table)
        logger.info(f"convert_spo_to_one_graph cost {time.time() - start_time}")
        res = list(one_graph_map.values())
        if len(res) > 0:
            return res
    except Exception as e:
        # Log the error or handle it appropriately
        logger.debug(f"An error occurred in recall_spo_by_spg_gql: {e}", exc_info=True)
    return []


def recall_one_hop_graph_by_entities(
    graph_api, heads: List[EntityData], tails: List[EntityData]
):
    one_hop_graph_list = []
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        map_dict = {"s": heads, "o": tails}
        for k, v in map_dict.items():
            if len(v) == 0:
                continue
            try:
                futures = [
                    executor.submit(graph_api.get_entity_one_hop, entity)
                    for entity in v
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]
                for r in results:
                    if r is None:
                        continue
                    r.s_alias_name = k
                    one_hop_graph_list.append(r)
            except Exception as e:
                logger.debug(
                    f"An error occurred in recall_one_hop_graph: {e}", exc_info=True
                )
    logger.info(f"recall_one_hop_graph cost {time.time() - start_time}")
    return one_hop_graph_list
