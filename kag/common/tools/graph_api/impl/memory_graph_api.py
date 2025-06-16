import logging
from typing import List, Dict

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import VectorizeModelABC


from kag.interface.solver.base_model import SPOEntity
from kag.interface.solver.model.one_hop_graph import (
    EntityData,
    OneHopGraphData,
)

from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.graph_api.model.table_model import TableData

logger = logging.getLogger()


@GraphApiABC.register("memory_graph_api")
class MemoryGraphApi(GraphApiABC):
    def __init__(self, graph_path, vectorize_model=None, **kwargs):
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.memory_graph_path = graph_path

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        from kag.common.graphstore.memory_graph import MemoryGraph

        self.graph = MemoryGraph(
            kag_project_config.namespace, self.memory_graph_path, vectorize_model
        )

    def get_entity(self, entity: SPOEntity) -> List[EntityData]:
        raise NotImplementedError()

    def get_entity_one_hop(self, entity: EntityData) -> OneHopGraphData:
        return self.graph.get_one_hop_graph(entity.biz_id, entity.type)

    def execute_dsl(self, dsl: str, **kwargs) -> TableData:
        raise NotImplementedError(f"{dsl}")

    def convert_spo_to_one_graph(self, table: TableData) -> Dict[str, OneHopGraphData]:
        raise NotImplementedError()

    def calculate_pagerank_scores(
        self, target_vertex_type, start_nodes: List[Dict], top_k=10
    ) -> Dict:
        ppr_list = self.graph.ppr_chunk_retrieval(start_nodes, topk=top_k)
        ppr_result = {}
        for node in ppr_list:
            ppr_result[node["node"]["id"]] = node
        return ppr_result

    def get_entity_prop_by_id(self, biz_id, label) -> Dict:
        entity: EntityData = self.graph.get_entity(biz_id=biz_id, label=label)
        datas = entity.to_json()
        if entity.prop:
            datas.update(entity.prop.get_properties_map())
        return datas


if __name__ == "__main__":
    vectorize_model = VectorizeModelABC.from_config(
        {
            "api_key": "key",
            "base_url": "https://api.siliconflow.cn/v1/",
            "model": "BAAI/bge-m3",
            "type": "openai",
            "vector_dimensions": 1024,
        }
    )
    graph_api = MemoryGraphApi(
        graph_path="KAG/kag/open_benchmark/musique/builder/ckpt/graph",
        vectorize_model=vectorize_model,
    )
    out = graph_api.get_entity_one_hop(
        EntityData(
            entity_id="408c1110674439a50dd1a107de36f04aa2af1833c8507e9826df695c3dba3f5b",
            node_type="MuSiQue.Chunk",
        )
    )
    print(out)
