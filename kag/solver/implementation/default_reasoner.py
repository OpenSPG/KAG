import json
import logging
import re
from typing import List

from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.common.base_model import LFPlanResult
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData
from kag.solver.logic.core_modules.common.utils import generate_random_string
from kag.solver.logic.core_modules.lf_solver import LFSolver
from knext.reasoner.rest.models.data_edge import DataEdge
from knext.reasoner.rest.models.data_node import DataNode
from knext.reasoner.rest.models.sub_graph import SubGraph

logger = logging.getLogger()


def convert_spo_to_graph(graph_id, spo_retrieved):
    nodes = {}
    edges = []
    for spo in spo_retrieved:

        def _get_node(entity: EntityData):
            node = DataNode(
                id=entity.to_show_id(),
                name=entity.get_short_name(),
                label=entity.type_zh,
                properties=entity.prop.get_properties_map() if entity.prop else {},
            )
            return node

        start_node = _get_node(spo.from_entity)
        end_node = _get_node(spo.end_entity)
        if start_node.id not in nodes:
            nodes[start_node.id] = start_node
        if end_node.id not in nodes:
            nodes[end_node.id] = end_node
        spo_id = spo.to_show_id()
        data_spo = DataEdge(
            id=spo_id,
            _from=start_node.id,
            from_type=start_node.label,
            to=end_node.id,
            to_type=end_node.label,
            properties=spo.prop.get_properties_map() if spo.prop else {},
            label=spo.type_zh,
        )
        edges.append(data_spo)
    sub_graph = SubGraph(
        class_name=graph_id, result_nodes=list(nodes.values()), result_edges=edges
    )
    return sub_graph


def update_sub_question_recall_docs(docs):
    """
    Update the context with retrieved documents for sub-questions.

    Args:
        docs (list): List of retrieved documents.

    Returns:
        list: Updated context content.
    """
    if docs is None or len(docs) == 0:
        return []
    doc_content = [f"## Chunk Retriever"]
    doc_content.extend(["|id|content|", "|-|-|"])
    for i, d in enumerate(docs, start=1):
        _d = d.replace("\n", "<br>")
        doc_content.append(f"|{i}|{_d}|")
    return doc_content


def convert_lf_res_to_report_format(
    kg_retriever, req_id, index, doc_retrieved, kg_graph: KgGraph
):
    context = []
    sub_graph = None
    spo_retrieved = kg_graph.get_all_spo()
    if len(spo_retrieved) > 0:
        spo_answer_path = json.dumps(
            kg_graph.to_answer_path(),
            ensure_ascii=False,
            indent=4,
        )
        spo_answer_path = f"```json\n{spo_answer_path}\n```"
        graph_id = f"{req_id}_{index}"
        graph_div = f"<div class='{graph_id}'></div>\n\n"
        sub_graph = convert_spo_to_graph(graph_id, spo_retrieved)
        context.append(graph_div)
        context.append(f"#### Triplet Retrieved:")
        context.append(spo_answer_path)
    elif kg_retriever is not None:
        context.append(f"#### Triplet Retrieved:")
        context.append("No triplets were retrieved.")

    context += update_sub_question_recall_docs(doc_retrieved)
    return context, sub_graph
class DefaultReasoner(KagReasonerABC):
    """
    A processor class for handling logical form tasks in language processing.

    This class uses an LLM module (llm_module) to plan, retrieve, and solve logical forms.

    Parameters:
    - lf_planner (LFBasePlanner): The planner for structuring logical forms. Defaults to None. If not provided, the default implementation of LFPlanner is used.
    - lf_solver: Instance of the logical form solver, which solves logical form problems. If not provided, the default implementation of LFSolver is used.

    Attributes:
    - lf_planner: Instance of the logical form planner.
    - lf_solver: Instance of the logical form solver, which solves logical form problems.
    - sub_query_total: Total number of sub-queries processed.
    - kg_direct: Number of direct knowledge graph queries.
    - trace_log: List to log trace information.
    """

    def __init__(self, lf_planner: LFPlannerABC = None, lf_solver: LFSolver = None, **kwargs):
        super().__init__(
            lf_planner=lf_planner,
            lf_solver=lf_solver,
            **kwargs
        )

        self.lf_planner = lf_planner or DefaultLFPlanner(**kwargs)
        self.lf_solver = lf_solver or LFSolver(
            kg_retriever=KGRetrieverByLlm(**kwargs),
            chunk_retriever=LFChunkRetriever(**kwargs),
            **kwargs
        )

        self.sub_query_total = 0
        self.kg_direct = 0
        self.trace_log = []

    def reason(self, question: str):
        """
        Processes a given question by planning and executing logical forms to derive an answer.

        Parameters:
        - question (str): The input question to be processed.

        Returns:
        - solved_answer: The final answer derived from solving the logical forms.
        - supporting_fact: Supporting facts gathered during the reasoning process.
        - history_log: A dictionary containing the history of QA pairs and re-ranked documents.
        """
        # logic form planing
        lf_nodes: List[LFPlanResult] = self.lf_planner.lf_planing(question)

        # logic form execution
        solved_answer, sub_qa_pair, recall_docs, history_qa_log, kg_graph = self.lf_solver.solve(question, lf_nodes)
        # Generate supporting facts for sub question-answer pair
        supporting_fact = '\n'.join(sub_qa_pair)

        # Retrieve and rank documents
        sub_querys = [lf.query for lf in lf_nodes]
        if self.lf_solver.chunk_retriever:
            docs = self.lf_solver.chunk_retriever.rerank_docs([question] + sub_querys, recall_docs)
        else:
            logger.info("DefaultReasoner not enable chunk retriever")
            docs = []
        history_log = {
            'history': history_qa_log,
            'rerank_docs': docs
        }
        if len(docs) > 0:
            # Append supporting facts for retrieved chunks
            supporting_fact += f"\nPassages:{str(docs)}"
        context = []
        if self.lf_solver.kg_retriever is not None:
            # process with retrieved graph
            logic_form_list = []
            for lf in lf_nodes:
                for l in lf.lf_nodes:
                    logic_form_list.append(str(l))
            sub_logic_nodes_str = "\n".join(logic_form_list)
            # 为产品展示隐藏冗余信息
            sub_logic_nodes_str = re.sub(
                r"(\s,sub_query=[^)]+|get\([^)]+\))", "", sub_logic_nodes_str
            ).strip()
            context = [
                "## SPO Retriever",
                "#### logic_form expression: ",
                f"```java\n{sub_logic_nodes_str}\n```",
            ]
        cur_content, sub_graph = self._convert_lf_res_to_report_format(
            req_id=f"graph_{generate_random_string(3)}",
            index=0,
            doc_retrieved=docs,
            kg_graph=kg_graph
        )
        context += cur_content

        history_log['report_info'] = {
            'context': context,
            'sub_graph': [sub_graph] if sub_graph else None

        }
        return solved_answer, supporting_fact, history_log

    def _convert_lf_res_to_report_format(
        self, req_id, index, doc_retrieved, kg_graph: KgGraph
    ):
        return convert_lf_res_to_report_format(self.lf_solver.kg_retriever, req_id, index, doc_retrieved, kg_graph)