import logging
from typing import List

from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.common.base_model import LFPlanResult
from kag.solver.logic.core_modules.lf_solver import LFSolver

logger = logging.getLogger()

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
        solved_answer, sub_qa_pair, recall_docs, history_qa_log = self.lf_solver.solve(question, lf_nodes)
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
        return solved_answer, supporting_fact, history_log
