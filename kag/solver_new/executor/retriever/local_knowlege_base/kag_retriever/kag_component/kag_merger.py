from typing import List

from kag.solver.logic.core_modules.common.one_hop_graph import RetrievedData
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.flow_component import \
    FlowComponent

@FlowComponent.register("kg_merger")
class KagMerger(FlowComponent):
    def __init__(self, top_k, **kwargs):
        super().__init__(**kwargs)
        self.top_k = top_k

    def invoke(self, datas: List[List[RetrievedData]], **kwargs) -> List[RetrievedData]:
        raise NotImplementedError("invoke not implemented yet.")
