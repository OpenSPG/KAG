from typing import List

from kag.interface.solver.base_model import SPOEntity, LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.kg_cs.kg_cs_retriever import \
    KGConstrainRetrieverABC
from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect


def _store_lf_node_structure(kg_graph: KgGraph, logic_node: GetSPONode):
    """Store logical node structure in knowledge graph

    Args:
        kg_graph (KgGraph): Knowledge graph instance
        logic_node (GetSPONode): Current logical node
    """
    predicate = logic_node.p.alias_name
    kg_graph.query_graph[predicate] = {
        "s": logic_node.s.alias_name,
        "p": predicate,
        "o": logic_node.o.alias_name,
    }


def _find_entities(kg_graph: KgGraph, symbol_entity: SPOEntity, query: str, el):
    # Try existing entities in knowledge graph
    entities = kg_graph.get_entity_by_alias(symbol_entity.alias_name)
    if entities:
        kg_graph.entity_map[symbol_entity.alias_name] = entities
        return entities
    # Perform entity linking if possible
    if symbol_entity.entity_name:
        entities = el.invoke(query, symbol_entity.get_mention_name(), symbol_entity.get_entity_first_type_or_un_std())
        if entities:
            kg_graph.entity_map[symbol_entity.alias_name] = entities
            return entities
    return []


class KgRetrieverTemplate:
    def __init__(self, path_select: PathSelect, entity_linking, **kwargs):
        super().__init__(**kwargs)
        self.path_select = path_select
        self.entity_linking = entity_linking

    def invoke(self, query: str, logic_nodes: List[LogicNode], graph_data: KgGraph = None, **kwargs) -> KgGraph:
        kg_graph = graph_data or KgGraph()
        for logic_node in logic_nodes:
            if isinstance(logic_node, GetSPONode):
                if logic_node.get_fl_node_result().spo:
                    continue
                select_rel = self._retrieved_on_graph(kg_graph, logic_node)
                logic_node.get_fl_node_result().spo = select_rel
                if select_rel and kwargs.get("is_exact_match", False):
                    logic_node.get_fl_node_result().summary = str(select_rel)

        return kg_graph

    def _retrieved_on_graph(self, kg_graph: KgGraph, logic_node: GetSPONode):

        _store_lf_node_structure(kg_graph, logic_node)
        head_entities = self._find_head_entities(kg_graph, logic_node)
        tail_entities = self._find_tail_entities(kg_graph, logic_node)
        if len(head_entities) == 0 and len(tail_entities) == 0:
            return []
        return self._retrieve_relations(kg_graph=kg_graph, logic_node=logic_node, head_entities=head_entities,
                                        tail_entities=tail_entities)

    def _retrieve_relations(
            self,
            kg_graph: KgGraph,
            logic_node: GetSPONode,
            head_entities: List[EntityData],
            tail_entities: List[EntityData]
    ):
        selected_relations = self.path_select.invoke(
            query=logic_node.sub_query, spo=logic_node, heads=head_entities, tails=tail_entities
        )
        predicate = logic_node.p.alias_name
        kg_graph.edge_map[predicate] = selected_relations
        return selected_relations

    def _find_tail_entities(
            self, kg_graph: KgGraph, logic_node: GetSPONode
    ) -> List[EntityData]:
        """Find tails entities for path selection

        Args:
            kg_graph (KgGraph): Current knowledge graph
            logic_node (GetSPONode): Current logical node

        Returns:
            List[EntityData]: List of found entities or None
        """
        return _find_entities(kg_graph, logic_node.o, logic_node.sub_query, self.entity_linking)

    def _find_head_entities(
            self, kg_graph: KgGraph, logic_node: GetSPONode
    ) -> List[EntityData]:
        """Find heads entities for path selection

        Args:
            kg_graph (KgGraph): Current knowledge graph
            logic_node (GetSPONode): Current logical node

        Returns:
            List[EntityData]: List of found entities or None
        """
        if isinstance(logic_node.s, SPOEntity):
            return _find_entities(kg_graph, logic_node.s, logic_node.sub_query, self.entity_linking)
        return []
