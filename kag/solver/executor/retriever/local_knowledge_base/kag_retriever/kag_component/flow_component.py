from typing import Optional, List

from kag.common.registry import Registrable
from kag.interface.solver.model.one_hop_graph import RetrievedData


class FlowComponent(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "")
        self.result: Optional[List[RetrievedData]] = None
        self.break_flag = False

    def invoke(self, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    def is_break(self):
        return self.break_flag

    def break_judge(self, **kwargs):
        self.break_flag = False
