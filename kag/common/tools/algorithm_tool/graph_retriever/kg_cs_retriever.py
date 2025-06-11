from kag.common.config import get_default_chat_llm_config
from kag.common.tools.algorithm_tool.graph_retriever.lf_kg_retriever_template import KgRetrieverTemplate
from kag.interface import LLMClient, RetrieverABC, RetrieverOutput, Context


from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)


@RetrieverABC.register("kg_cs_open_spg")
class KgConstrainRetrieverWithOpenSPGRetriever(RetrieverABC):
    def __init__(
        self,
        path_select: PathSelect = None,
        entity_linking: EntityLinking =None,
        llm: LLMClient = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_cs")
        self.llm = llm or LLMClient.from_config(get_default_chat_llm_config())
        self.path_select = path_select or PathSelect.from_config(
            {"type": "exact_one_hop_select"}
        )
        if isinstance(entity_linking, dict):
            entity_linking = EntityLinking.from_config(entity_linking)
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {
                "type": "default_entity_linking",
                "recognition_threshold": 0.9,
                "exclude_types": ["Chunk"],
            }
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select,
            entity_linking=self.entity_linking,
            llm_module=self.llm,
        )

    def invoke(self, task, **kwargs) -> RetrieverOutput:

        query = task.arguments.get(
            "rewrite_query", task.arguments["query"]
        )
        logical_node = task.arguments.get("logic_form_node", None)
        if not logical_node:
            return RetrieverOutput(
                retriever_method=self.schema().get("name", ""),
                err_msg="No logic node found in task arguments",
            )
        context = kwargs.get("context", Context())

        kg_graph = self.template.invoke(
                query=query,
                logic_nodes=[logical_node],
                graph_data=context.variables_graph,
                is_exact_match=True,
                name=self.name,
                **kwargs
            )
        return RetrieverOutput(
                retriever_method=self.schema().get("name", ""),
                graphs=[kg_graph]
            )

    def schema(self):
        return {
            "name": "kg_cs_retriever",
            "description": "Retrieve graph data in knowledge graph cs level",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for context retrieval",
                    },
                    "logic_form_node": {
                        "type": "object",
                        "description": "Logic node for context retrieval",
                    }
                },
                "required": ["query", "logic_form_node"],
            },
        }