from typing import List

from kag.interface import ToolABC
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData, RelationData
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect


@ToolABC.register("hybrid_one_hop_select")
class HybridOneHopSelect(PathSelect):
    """Hybrid path selection tool combining exact and fuzzy strategies.

    This class implements a composite path selection strategy that first attempts
    exact matching and falls back to fuzzy matching when no results are found.
    It aggregates the capabilities of two underlying PathSelect implementations.

    Args:
        exact_select (PathSelect): Exact-match path selector for precise queries
        fuzzy_select (PathSelect): Fuzzy-match path selector for approximate matches
    """

    def __init__(self, exact_select: PathSelect, fuzzy_select: PathSelect):
        """Initialize hybrid selector with exact and fuzzy components."""
        super().__init__()
        self.exact_select = exact_select  # Precise path selection strategy
        self.fuzzy_select = fuzzy_select  # Approximate/fuzzy selection strategy

    def invoke(self, query, spo: GetSPONode, heads: List[EntityData], tails: List[EntityData], **kwargs) -> List[RelationData]:
        """Execute hybrid path selection strategy.

        First tries exact matching, then falls back to fuzzy matching if no results found.

        Args:
            query (str): User input query text
            spo (GetSPONode): SPO (Subject-Predicate-Object) logic node structure
            entity (EntityData): Target entity for path exploration
            **kwargs: Additional parameters propagated to selectors

        Returns:
            List[RelationData]: Selected one-hop relation paths (exact if possible)

        Raises:
            RuntimeError: If both selectors fail to produce results
        """
        exact_results = self.exact_select.invoke(query, spo, heads, tails, **kwargs)
        if exact_results:
            return exact_results
        else:
            return self.fuzzy_select.invoke(query, spo, heads, tails, **kwargs)
