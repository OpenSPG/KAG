from typing import List

from kag.common.conf import KAG_PROJECT_CONF, KAG_CONFIG
from kag.interface import VectorizeModelABC
from kag.tools.search_api.search_api_abc import SearchApiABC


@SearchApiABC.register("memory_search_api")
class MemorySearchAPI(SearchApiABC):
    def __init__(self, graph_path, vectorize_model=None, **kwargs):
        super().__init__(**kwargs)
        self.memory_graph_path = graph_path

        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            KAG_CONFIG.all_config["vectorize_model"]
        )
        from kag.common.graphstore.memory_graph import MemoryGraph

        self.graph = MemoryGraph(
            KAG_PROJECT_CONF.namespace, self.memory_graph_path, vectorize_model
        )

    def search_text(
        self, query_string, label_constraints=None, topk=10, params=None
    ) -> List:
        return []

    def search_vector(
        self, label, property_key, query_vector, topk=10, ef_search=None, params=None
    ) -> List:
        res = self.graph.batch_vector_search(
            label=label,
            property_key=property_key,
            query_vector=[query_vector],
            topk=topk,
        )
        if res:
            return res[0]
        return []


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
    import time

    start_time = time.time()
    graph_api = MemorySearchAPI(
        graph_path="/KAG/kag/open_benchmark/musique/builder/ckpt/graph",
        vectorize_model=vectorize_model,
    )
    print(f"{time.time() - start_time}")
    start_time = time.time()
    graph_api2 = MemorySearchAPI(
        graph_path="/KAG/kag/open_benchmark/musique/builder/ckpt/graph",
        vectorize_model=vectorize_model,
    )
    print(f"{time.time() - start_time}")
    name = "Jesús Aranguren_split_0"
    name_v = vectorize_model.vectorize(name)
    out = graph_api.search_vector(
        label="MuSiQue.Chunk", property_key="name", query_vector=name_v
    )
    print(out)
