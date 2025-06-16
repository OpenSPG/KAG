import logging
from typing import Optional


from kag.common.config import LogicFormConfiguration
from kag.common.text_sim_by_vector import TextSimilarity
from kag.interface import VectorizeModelABC, RetrieverABC, RetrieverOutput
from kag.interface.solver.model.schema_utils import SchemaUtils


from kag.common.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import (
    VectorChunkRetriever,
)
from kag.common.tools.graph_api.graph_api_abc import GraphApiABC
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@RetrieverABC.register("rc_open_spg")
class RCRetrieverOnOpenSPG(RetrieverABC):
    def __init__(
        self,
        top_k=10,
        vector_chunk_retriever: VectorChunkRetriever = None,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        graph_api: GraphApiABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_rc")
        self.top_k = top_k
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            self.kag_config.all_config["vectorize_model"]
        )
        self.text_similarity = TextSimilarity(vectorize_model)

        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )

        self.vector_chunk_retriever = vector_chunk_retriever or VectorChunkRetriever(
            vectorize_model=self.vectorize_model, search_api=self.search_api
        )

        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": self.kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                }
            )
        )

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        output = self.vector_chunk_retriever.invoke(task=task, **kwargs)
        output.retriever_method = self.schema().get("name", "")
        return output

    def schema(self):
        return {
            "name": "kg_rc_retriever",
            "description": "Retrieve chunk data",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    }
                },
                "required": ["query"],
            },
        }
