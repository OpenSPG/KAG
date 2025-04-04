from typing import List

from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.one_hop_graph import KgGraph
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)


class KGFreeRetrieverABC(FlowComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "kg_fr"

    def invoke(
        self, query: str, logic_nodes: List[LogicNode], graph_data: KgGraph, **kwargs
    ) -> KgGraph:
        raise NotImplementedError("invoke not implemented yet.")

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
