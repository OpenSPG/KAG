import logging
from typing import List, Dict, Tuple

from kag.solver.execute.op_executor.op_executor import OpExecutor
from kag.interface.solver.base_model import LogicNode, SPOEntity, SPOBase
from kag.solver.logic.core_modules.common.one_hop_graph import (
    EntityData,
    KgGraph,
    RelationData,
)
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.retriever.base.kg_retriever import KGRetriever
from kag.solver.retriever.exact_kg_retriever import ExactKgRetriever
from kag.solver.retriever.fuzzy_kg_retriever import FuzzyKgRetriever

logger = logging.getLogger()


def _get_entity_node_from_lf(e: SPOEntity):
    if not e.id_set:
        return []
    ret = []
    for biz_id in e.id_set:
        d = EntityData()
        d.biz_id = biz_id
        d.type = e.get_entity_first_std_type()
        d.type_zh = e.get_un_std_entity_first_type_or_std()
        ret.append(d)
    return ret


class GetSPOExecutor(OpExecutor):
    """
    Executor for the 'get_spo' operator.

    This class is used to retrieve one-hop graphs based on the given parameters.
    It extends the base `OpExecutor` class and initializes additional components specific to retrieving SPO triples.
    """

    def __init__(
        self,
        schema: SchemaUtils,
        **kwargs,
    ):
        """
        Initializes the GetSPOExecutor with necessary components.

        Parameters:
            schema (SchemaUtils): Semantic structure definition to assist in the parsing process.
        """
        super().__init__(schema, **kwargs)

        self.exact_kg_retriever: ExactKgRetriever = kwargs.get("exact_kg_retriever")
        self.fuzzy_kg_retriever: FuzzyKgRetriever = kwargs.get("fuzzy_kg_retriever")

    def get_mentioned_entity(self, n: GetSPONode, kg_graph: KgGraph):
        entities_candis = []
        s_data = kg_graph.get_entity_by_alias(n.s.alias_name)
        if (
            s_data is None
            and isinstance(n.s, SPOEntity)
            and n.s.entity_name
            and len(n.s.id_set) == 0
        ):
            entities_candis.append(n.s)

        el_kg_graph = KgGraph()
        if isinstance(n, GetSPONode):
            o_data = kg_graph.get_entity_by_alias(n.o.alias_name)
            if (
                o_data is None
                and isinstance(n.o, SPOEntity)
                and n.o.entity_name
                and len(n.o.id_set) == 0
            ):
                entities_candis.append(n.o)
            el_kg_graph.query_graph[n.p.alias_name] = {
                "s": n.s.alias_name,
                "p": n.p.alias_name,
                "o": n.o.alias_name,
            }
        return entities_candis

    def _get_start_node_list(self, s: SPOBase, kg_graph: KgGraph) -> List[EntityData]:
        s_data_set = []
        if isinstance(s, SPOEntity) and len(s.id_set) > 0:
            s_data_set = _get_entity_node_from_lf(s)
        else:
            s_data_set_up = kg_graph.get_entity_by_alias(s.alias_name)
            if s_data_set_up is not None:
                for s_data in s_data_set_up:
                    if isinstance(s_data, EntityData) and s_data.type != "attribute":
                        s_data_set.append(s_data)
                    if isinstance(s_data, RelationData):
                        s_data_set.append(s_data)
        return s_data_set

    def _kg_match(
        self,
        logic_node: GetSPONode,
        req_id: str,
        kg_retriever: KGRetriever,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Tuple[bool, KgGraph]:
        if not isinstance(logic_node, GetSPONode):
            return False, KgGraph()

        n: GetSPONode = logic_node

        copy_kg_graph = KgGraph()
        copy_kg_graph.merge_kg_graph(kg_graph)
        copy_kg_graph.query_graph[n.p.alias_name] = {
            "s": n.s.alias_name,
            "p": n.p.alias_name,
            "o": n.o.alias_name,
        }
        mentioned_entities = self.get_mentioned_entity(n, copy_kg_graph)
        if mentioned_entities:
            el_kg_graph = KgGraph()
            el_kg_graph.query_graph[n.p.alias_name] = {
                "s": n.s.alias_name,
                "p": n.p.alias_name,
                "o": n.o.alias_name,
            }
            for mentioned_entity in mentioned_entities:
                linked_entities: List[EntityData] = kg_retriever.retrieval_entity(
                    mentioned_entity, kwargs=param
                )
                for entity_id_info in linked_entities:
                    entity_type_zh = (
                        self.schema.node_en_zh[
                            self.schema.get_label_without_prefix(entity_id_info.type)
                        ]
                        if self.schema is not None
                        and self.schema.get_label_without_prefix(entity_id_info.type)
                        in self.schema.node_en_zh.keys()
                        else None
                    )
                    entity_id_info.type_zh = entity_type_zh
                el_kg_graph.nodes_alias.append(mentioned_entity.alias_name)
                el_kg_graph.entity_map[mentioned_entity.alias_name] = linked_entities
            copy_kg_graph.merge_kg_graph(el_kg_graph)

        s_data_set = self._get_start_node_list(n.s, copy_kg_graph)
        o_data_set = self._get_start_node_list(n.o, copy_kg_graph)
        if len(s_data_set) == 0 and len(o_data_set) == 0:
            return False, copy_kg_graph

        one_hop_graph_list = kg_retriever.recall_one_hop_graph(
            logic_node, s_data_set, o_data_set, kwargs=param
        )
        cur_kg_graph = kg_retriever.retrieval_relation(
            logic_node, one_hop_graph_list, kwargs=param
        )
        spo_res = cur_kg_graph.get_entity_by_alias(n.p.alias_name)
        if not spo_res:
            return False, copy_kg_graph
        cur_kg_graph.nodes_alias.append(n.s.alias_name)
        cur_kg_graph.nodes_alias.append(n.o.alias_name)
        cur_kg_graph.edge_alias.append(n.p.alias_name)
        copy_kg_graph.merge_kg_graph(cur_kg_graph)
        process_info[logic_node.sub_query]["spo_retrieved"] = spo_res
        process_info[logic_node.sub_query]["match_type"] = (
            "exact spo" if isinstance(kg_retriever, ExactKgRetriever) else "fuzzy spo"
        )
        return True, copy_kg_graph

    def executor(
        self,
        nl_query: str,
        logic_node: LogicNode,
        req_id: str,
        kg_graph: KgGraph,
        process_info: dict,
        param: dict,
    ) -> Dict:
        if not isinstance(logic_node, GetSPONode):
            return {}
        n = logic_node

        kg_graph.logic_form_base[n.s.alias_name] = n.s
        kg_graph.logic_form_base[n.p.alias_name] = n.p
        kg_graph.logic_form_base[n.o.alias_name] = n.o

        is_success, exact_matched_graph = self._kg_match(
            n, req_id, self.exact_kg_retriever, kg_graph, process_info, param
        )
        if is_success:
            kg_graph.merge_kg_graph(exact_matched_graph)
            return process_info[logic_node.sub_query]

        _, fuzzy_matched_graph = self._kg_match(
            n, req_id, self.fuzzy_kg_retriever, kg_graph, process_info, param
        )
        kg_graph.merge_kg_graph(fuzzy_matched_graph)
        return process_info[logic_node.sub_query]
