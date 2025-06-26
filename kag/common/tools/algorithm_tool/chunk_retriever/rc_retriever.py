import logging
import time

from kag.common.config import LogicFormConfiguration
from kag.common.text_sim_by_vector import TextSimilarity
from kag.interface import VectorizeModelABC, RetrieverABC, RetrieverOutput
from kag.interface.solver.model.schema_utils import SchemaUtils


from kag.common.tools.algorithm_tool.chunk_retriever.vector_chunk_retriever import (
    VectorChunkRetriever,
)
from kag.common.tools.search_api.search_api_abc import SearchApiABC

logger = logging.getLogger()


@RetrieverABC.register("rc_open_spg")
class RCRetrieverOnOpenSPG(RetrieverABC):
    def __init__(
        self,
        search_api: SearchApiABC,
        vectorize_model: VectorizeModelABC,
        vector_chunk_retriever: VectorChunkRetriever = None,
        top_k=10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.top_k = top_k
        self.vectorize_model = vectorize_model
        self.text_similarity = TextSimilarity(vectorize_model)

        self.search_api = search_api

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
        start_time = time.time()
        try:
            output = self.vector_chunk_retriever.invoke(task=task, **kwargs)
            output.retriever_method = self.name
        except Exception as e:
            logger.error(e, exc_info=True)
            output = RetrieverOutput(retriever_method=self.name, err_msg=f"{task} {e}")
        logger.debug(
            f"{self.schema().get('name', '')} `{task.arguments['query']}`  Retrieved chunks num: {len(output.chunks)} cost={time.time() - start_time}"
        )
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
