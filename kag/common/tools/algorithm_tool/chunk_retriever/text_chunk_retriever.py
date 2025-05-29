import logging

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.tools.search_api.search_api_abc import SearchApiABC
from knext.schema.client import CHUNK_TYPE
from kag.interface import RetrieverABC, ChunkData, RetrieverOutput

logger = logging.getLogger()


@RetrieverABC.register("text_chunk_retriever")
class TextChunkRetriever(RetrieverABC):
    def __init__(self, search_api: SearchApiABC = None, top_k: int = 10, **kwargs):
        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        super().__init__(top_k, **kwargs)

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        top_k = kwargs.get("top_k", self.top_k)
        query = task.arguments["query"]
        try:
            top_k_docs = self.search_api.search_text(
                label_constraints=[
                    self.schema_helper.get_label_within_prefix(CHUNK_TYPE)
                ],
                query_string=query,
                topk=top_k,
            )

            chunks = []
            for item in top_k_docs:
                chunks.append(
                    ChunkData(
                        content=item["node"]["content"],
                        title=item["node"]["name"],
                        chunk_id=item["node"]["id"],
                        score=item["score"],
                    )
                )
            return RetrieverOutput(chunks=chunks, retriever_method=self.schema().get("name", ""))
        except Exception as e:
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
            return RetrieverOutput()

    def schema(self):
        return {
            "name": "text_chunk_retriever",
            "description": "Retrieve relevant text chunks from document store using text similarity search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for retrieving relevant text chunks",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }
