from typing import List

from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)


class KGConstrainRetrieverABC(FlowComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def invoke(self, query: str, logic_nodes: List[LogicNode], **kwargs) -> KgGraph:
        raise NotImplementedError("invoke not implemented yet.")

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
