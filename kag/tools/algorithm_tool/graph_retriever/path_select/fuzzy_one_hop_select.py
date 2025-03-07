from typing import List

from kag.interface import ToolABC
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, RelationData
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect


@ToolABC.register("fuzzy_one_hop_select")
class FuzzyOneHopSelect(PathSelect):
    def __init__(self):
        super().__init__()

    def invoke(self, query, spo: GetSPONode, entity: EntityData, **kwargs) -> List[RelationData]:
        raise NotImplementedError("invoke not implemented yet.")
