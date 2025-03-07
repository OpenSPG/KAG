from typing import List

from kag.interface import ToolABC
from kag.solver.logic.core_modules.common.one_hop_graph import EntityData

@ToolABC.register("ppr_chunk_retriever")
class PprChunkRetriever(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(self, query, start_entities: List[EntityData], top_k: int, **kwargs)->List[str]:
        raise NotImplementedError("invoke not implemented yet.")

    def schema(self):
        return {
            "name": "ppr_chunk_retriever",
            "description": "Retrieve document chunks using Personalized PageRank algorithm with knowledge graph entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval"
                    },
                    "start_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Entity ID in knowledge graph"},
                                "type": {"type": "string", "description": "Entity type category"},
                                "name": {"type": "string", "description": "Canonical entity name"},
                                "score": {"type": "string", "description": "The weight of this entity"}
                            },
                            "required": ["id", "name", "score"]
                        },
                        "description": "Seed entities for personalized PageRank calculation"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top-ranked chunks to return",
                        "default": 5,
                        "minimum": 1
                    }
                },
                "required": ["query", "start_entities"]
            }
        }
