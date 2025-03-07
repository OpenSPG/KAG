from kag.interface import ExecutorABC, LLMClient
from kag.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.tools.algorithm_tool.graph_retriever.path_select.path_select import PathSelect
from kag.tools.algorithm_tool.ner import Ner


class KGRetrieverExecutor(ExecutorABC):
    def __init__(self,
                 ner: Ner,
                 entity_linking: EntityLinking,
                 path_select: PathSelect,
                 llm_client: LLMClient
                 ):
        super().__init__()

    def invoke(self, query, task, context, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")


    def schema(self):
        return {
            "name": "kg_retriever_executor",
            "description": "Retrieve knowledge graph paths based on query and context to answer questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User input question or query text"
                    }
                },
                "required": ["query"]
            }
        }