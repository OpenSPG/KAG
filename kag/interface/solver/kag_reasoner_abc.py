from abc import abstractmethod
from typing import Tuple

from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.common.base import KagBaseModule
from kag.solver.logic.core_modules.lf_solver import LFSolver


class KagReasonerABC(KagBaseModule):
    """
    A processor class for handling logical form tasks in language processing.

    This class uses an LLM module (llm_module) to plan, retrieve, and solve logical forms.

    Parameters:
    - llm_module: The language model module used for generating and processing logical forms.
    - lf_planner (LFBasePlanner): The planner for structuring logical forms. Defaults to None. If not provided, the default implementation of LFPlanner is used.
    - lf_solver: Instance of the logical form solver, which solves logical form problems.

    Attributes:
    - lf_planner: Instance of the logical form planner.
    - lf_solver: Instance of the logical form solver, which solves logical form problems.
    - sub_query_total: Total number of sub-queries processed.
    - kg_direct: Number of direct knowledge graph queries.
    - trace_log: List to log trace information.
    """
    def __init__(self, lf_planner: LFPlannerABC = None, lf_solver: LFSolver = None, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def reason(self, question: str) -> Tuple[str, str, dict]:
        """
        Processes a given question by planning and executing logical forms to derive an answer.

        Parameters:
        - question (str): The input question to be processed.

        Returns:
        Tuple
        - solved_answer: The final answer derived from solving the logical forms.
        - supporting_fact: Supporting facts gathered during the reasoning process.
        - history_log: A dictionary containing the history of QA pairs and re-ranked documents.
        """