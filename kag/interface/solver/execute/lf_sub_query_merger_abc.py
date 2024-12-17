from typing import List

from kag.common.registry import Registrable
from abc import ABC, abstractmethod

from kag.solver.logic.core_modules.common.base_model import LFExecuteResult, LFPlan, SubQueryResult


class LFSubQueryResMerger(Registrable, ABC):
    """
    Initializes the base planner.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def merge(self, query, lf_sub_res: List[LFPlan]) -> LFExecuteResult:
        pass

