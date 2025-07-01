import knext.common.cache
import logging
from typing import Dict

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import ToolABC, VectorizeModelABC
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.tools.search_api.search_api_abc import SearchApiABC

from knext.schema.client import CHUNK_TYPE

logger = logging.getLogger()
chunk_cached_by_query_map = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@ToolABC.register("vector_chunk_retriever_legacy")
class VectorChunkRetriever(ToolABC):
    def __init__(
        self,
        vectorize_model: VectorizeModelABC = None,
        search_api: SearchApiABC = None,
        **kwargs,
    ):
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.vectorize_model = vectorize_model or VectorizeModelABC.from_config(
            kag_config.all_config["vectorize_model"]
        )
        self.search_api = search_api or SearchApiABC.from_config(
            {"type": "openspg_search_api"}
        )
        self.schema_helper: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": kag_project_config.project_id,
                    "KAG_PROJECT_HOST_ADDR": kag_project_config.host_addr,
                }
            )
        )

    def invoke(self, query, top_k: int, **kwargs) -> Dict[str, dict]:
        try:
            scores = chunk_cached_by_query_map.get(query)
            if scores and len(scores) > top_k:
                return scores
            if not query:
                logger.error("chunk query is emtpy", exc_info=True)
                return {}
            query_vector = self.vectorize_model.vectorize(query)
            top_k_docs = self.search_api.search_vector(
                label=self.schema_helper.get_label_within_prefix(CHUNK_TYPE),
                property_key="content",
                query_vector=query_vector,
                topk=top_k,
            )
            scores = {
                item["node"]["id"]: {
                    "score": item["score"],
                    "content": item["node"]["content"],
                    "name": item["node"]["name"],
                }
                for item in top_k_docs
            }
            chunk_cached_by_query_map.put(query, scores)
        except Exception as e:
            scores = dict()
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
        return scores

    def schema(self):
        return {
            "name": "vector_chunk_retriever",
            "description": "Retrieve relevant text chunks from document store using vector similarity search",
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
