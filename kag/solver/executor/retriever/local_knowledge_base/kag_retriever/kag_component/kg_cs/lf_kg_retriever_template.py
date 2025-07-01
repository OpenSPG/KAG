import logging
from typing import List, Optional
from tenacity import retry, stop_after_attempt

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import LLMClient
from kag.interface.solver.base_model import SPOEntity, LogicNode
from kag.interface.solver.reporter_abc import ReporterABC
from kag.interface.solver.model.one_hop_graph import KgGraph, EntityData
from kag.common.parser.logic_node_parser import GetSPONode

from kag.solver.utils import init_prompt_with_fallback
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)

logger = logging.getLogger()


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
    entities = kg_graph.get_entity_by_alias_without_attr(symbol_entity.alias_name)
    if entities:
        return entities
    # Perform entity linking if possible
    if symbol_entity.entity_name:
        entities = el.invoke(
            query,
            symbol_entity.get_mention_name(),
            symbol_entity.get_entity_type_or_un_std_list(),
        )
        if entities:
            kg_graph.entity_map[symbol_entity.alias_name] = entities
            return entities
    return []


class KgRetrieverTemplate:
    def __init__(
        self, path_select: PathSelect, entity_linking, llm_module: LLMClient, **kwargs
    ):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.path_select = path_select
        self.entity_linking = entity_linking
        self.solve_question_without_docs_prompt = init_prompt_with_fallback(
            "solve_question_without_docs", kag_project_config.biz_scene
        )
        self.llm_module = llm_module

    @retry(stop=stop_after_attempt(3), reraise=True)
    def generate_sub_answer(
        self, question: str, knowledge_graph: [], history_qa=[], **kwargs
    ):
        """
        Generates a sub-answer based on the given question, knowledge graph, documents, and history.

        Parameters:
        question (str): The main question to answer.
        knowledge_graph (list): A list of knowledge graph data.
        docs (list): A list of documents related to the question.
        history (list, optional): A list of previous query-answer pairs. Defaults to an empty list.

        Returns:
        str: The generated sub-answer.
        """
        if not knowledge_graph:
            return "I don't know"
        prompt = self.solve_question_without_docs_prompt
        params = {
            "question": question,
            "knowledge_graph": str(knowledge_graph),
            "history": "\n".join(history_qa),
        }
        llm_output = self.llm_module.invoke(
            params, prompt, with_json_parse=False, with_except=True, **kwargs
        )
        if llm_output and "i don't know" not in llm_output.lower():
            return llm_output
        return ""

    def invoke(
        self,
        query: str,
        logic_nodes: List[LogicNode],
        graph_data: KgGraph = None,
        **kwargs,
    ) -> KgGraph:
        segment_name = kwargs.get("segment_name", "thinker")
        component_name = kwargs.get("name", "")
        kg_graph = graph_data or KgGraph()
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        used_lf = []
        for logic_node in logic_nodes:
            if logic_node.get_fl_node_result().summary:
                used_lf.append(logic_node)
                continue
            if isinstance(logic_node, GetSPONode):
                if logic_node.get_fl_node_result().spo:
                    continue

                if reporter:
                    reporter.add_report_line(
                        segment_name,
                        f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                        logic_node.sub_query,
                        "INIT",
                        component_name=component_name,
                    )
                    reporter.add_report_line(
                        segment_name,
                        f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                        "task_executing",
                        "RUNNING",
                        component_name=component_name,
                    )

                try:
                    select_rel = self._retrieved_on_graph(kg_graph, logic_node)
                    logic_node.get_fl_node_result().spo = select_rel
                    if select_rel:
                        if kwargs.get("is_exact_match", False):
                            logic_node.get_fl_node_result().summary = str(select_rel)
                            # updated alias with spo
                            kg_graph.add_answered_alias(
                                logic_node.s.alias_name.alias_name, select_rel
                            )
                            kg_graph.add_answered_alias(
                                logic_node.p.alias_name.alias_name, select_rel
                            )
                            kg_graph.add_answered_alias(
                                logic_node.o.alias_name.alias_name, select_rel
                            )

                except Exception as e:
                    if reporter:
                        reporter.add_report_line(
                            segment_name,
                            f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                            f"failed: reason={e}",
                            "ERROR",
                            component_name=component_name,
                        )
                    logger.info(f"_retrieved_on_graph failed {e}", exc_info=True)

        return kg_graph

    def _retrieved_on_graph(self, kg_graph: KgGraph, logic_node: GetSPONode):
        _store_lf_node_structure(kg_graph, logic_node)
        head_entities = self._find_head_entities(kg_graph, logic_node)
        tail_entities = self._find_tail_entities(kg_graph, logic_node)
        if len(head_entities) == 0 and len(tail_entities) == 0:
            return []
        return self._retrieve_relations(
            kg_graph=kg_graph,
            logic_node=logic_node,
            head_entities=head_entities,
            tail_entities=tail_entities,
        )

    def _retrieve_relations(
        self,
        kg_graph: KgGraph,
        logic_node: GetSPONode,
        head_entities: List[EntityData],
        tail_entities: List[EntityData],
    ):
        kg_graph.nodes_alias.append(logic_node.s.alias_name)
        kg_graph.nodes_alias.append(logic_node.o.alias_name)
        kg_graph.edge_alias.append(logic_node.p.alias_name)

        selected_relations = self.path_select.invoke(
            query=logic_node.sub_query,
            spo=logic_node,
            heads=head_entities,
            tails=tail_entities,
        )
        predicate = logic_node.p.alias_name
        if selected_relations:
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
        return _find_entities(
            kg_graph, logic_node.o, logic_node.sub_query, self.entity_linking
        )

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
            return _find_entities(
                kg_graph, logic_node.s, logic_node.sub_query, self.entity_linking
            )
        return []
