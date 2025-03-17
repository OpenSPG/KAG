from typing import Optional, Dict, List

from kag.solver.logic.core_modules.common.one_hop_graph import EntityData


class RetrievedData:
    def __init__(self):
        pass


class NodeData:
    def __init__(self):
        self.id = None
        self.type = None
        self.properties = []
        self.score = 1.0


class EdgeData:
    def __init__(self):
        self.head: Optional[EntityData] = None
        self.tail: Optional[EntityData] = None
        self.rel_type = None
        self.properties = []
        self.score = 1.0


class GraphData(RetrievedData):
    def __init__(self):
        super().__init__()
        self.nodes: Dict[str, List[NodeData]] = {}
        self.edges: Dict[str, List[EdgeData]] = {}
        self.pattern_graph = {}

    def merge_graph(self, other):
        pass

    def get_all_edges(self) -> List[EdgeData]:
        all_edges = []
        for edge_list in self.edges.values():
            all_edges.extend(edge_list)
        return all_edges


class ChunkData(RetrievedData):
    def __init__(self):
        super().__init__()
        self.content = ""
        self.title = ""
        self.chunk_id = ""
        self.score = 1.0
