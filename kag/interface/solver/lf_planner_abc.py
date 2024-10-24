import os
from abc import ABC, abstractmethod
from typing import List

from kag.solver.common.base import KagBaseModule
from kag.solver.logic.core_modules.common.base_model import LFPlanResult


class LFPlannerABC(KagBaseModule, ABC):
    """
    Initializes the base planner.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.host_addr = kwargs.get("KAG_PROJECT_HOST_ADDR") or os.getenv("KAG_PROJECT_HOST_ADDR")
        self.project_id = kwargs.get("KAG_PROJECT_ID") or os.getenv("KAG_PROJECT_ID")

    @abstractmethod
    def lf_planing(self, question, llm_output=None) -> List[LFPlanResult]:
        """
        Method that should be implemented by all subclasses for planning logic.
        This is a default impl

         :
        question (str): The question or task to plan.
        llm_output (Any, optional): Output from the LLM module. Defaults to None.

        Returns:
        list of LFPlanResult
        """
        pass