from typing import List

from kag.interface.solver.model.one_hop_graph import RetrievedData
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)


@FlowComponent.register("kg_merger")
class KagMerger(FlowComponent):
    def __init__(self, top_k, **kwargs):
        super().__init__(**kwargs)
        self.top_k = top_k

    def invoke(self, datas: List[List[RetrievedData]], **kwargs) -> List[RetrievedData]:
        raise NotImplementedError("invoke not implemented yet.")
