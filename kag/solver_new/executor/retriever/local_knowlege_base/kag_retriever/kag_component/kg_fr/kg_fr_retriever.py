from typing import List

from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.flow_component import \
    FlowComponent
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.logic_node.logic_node import \
    LogicNode
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.retrieved_data import GraphData


class KGFreeRetrieverABC(FlowComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def invoke(self, query: str, logic_nodes: List[LogicNode], graph_data: GraphData, **kwargs) -> GraphData:
        raise NotImplementedError("invoke not implemented yet.")