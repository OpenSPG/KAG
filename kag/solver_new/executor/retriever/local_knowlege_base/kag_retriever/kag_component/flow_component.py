from typing import Optional, List

from kag.common.registry import Registrable
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.retrieved_data import RetrievedData


class FlowComponent(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs.get('name', '')
        self.result: Optional[List[RetrievedData]] = None

    def invoke(self, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")