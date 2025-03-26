from typing import List

from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, ChunkData
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)


class RCRetrieverABC(FlowComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def invoke(
        self, query, logic_nodes: List[LogicNode], graph_data: KgGraph, **kwargs
    ) -> List[ChunkData]:
        raise NotImplementedError("invoke not implemented yet.")

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
