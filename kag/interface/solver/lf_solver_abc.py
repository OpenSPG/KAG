from abc import ABC, abstractmethod


class LFSolverABC(ABC):
    """
    Initializes the base planner.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def solve(self, query, lf_nodes):
        pass
