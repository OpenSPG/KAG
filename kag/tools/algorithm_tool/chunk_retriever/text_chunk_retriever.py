import logging
from typing import Dict

from kag.common.conf import KAG_PROJECT_CONF
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.tools.search_api.search_api_abc import SearchApiABC
from knext.schema.client import CHUNK_TYPE
from kag.interface import ToolABC

logger = logging.getLogger()


@ToolABC.register("text_chunk_retriever")
class TextChunkRetriever(ToolABC):
    def __init__(self, search_api: SearchApiABC = None):
        super().__init__()
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

    def invoke(self, query, top_k: int, **kwargs) -> Dict[str, dict]:
        try:
            top_k_docs = self.search_api.search_text(
                label_constraints=[
                    self.schema_helper.get_label_within_prefix(CHUNK_TYPE)
                ],
                query_string=query,
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
        except Exception as e:
            scores = dict()
            logger.error(f"run calculate_sim_scores failed, info: {e}", exc_info=True)
        return scores

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
