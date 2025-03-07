from typing import List

from kag.interface import ToolABC

@ToolABC.register("vector_chunk_retriever")
class VectorChunkRetriever(ToolABC):
    def __init__(self):
        super().__init__()

    def invoke(self, query, top_k:int, **kwargs)->List[str]:
        raise NotImplementedError("invoke not implemented yet.")

    def schema(self):
        return {
            "name": "vector_chunk_retriever",
            "description": "Retrieve relevant text chunks from document store using vector similarity search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for retrieving relevant text chunks"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }