from abc import abstractmethod
from typing import Dict, List

from kag.common.registry import Registrable
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, OneHopGraphData


class GraphApiABC(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def get_entity(self, entity: SPOEntity) -> List[EntityData]:
        pass

    @abstractmethod
    def get_entity_one_hop(self, entity: EntityData) -> OneHopGraphData:
        pass

    @abstractmethod
    def execute_dsl(self, dsl: str) -> Dict[str, OneHopGraphData]:
        pass