import logging
import time

from kag.common.config import get_default_chat_llm_config
from kag.common.parser.schema_std import StdSchema
from kag.common.tools.algorithm_tool.graph_retriever.lf_kg_retriever_template import (
    KgRetrieverTemplate,
    get_std_logic_form_parser,
    std_logic_node,
)
from kag.interface import LLMClient, RetrieverABC, RetrieverOutput, Context


from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)

logger = logging.getLogger()


@RetrieverABC.register("kg_cs_open_spg")
class KgConstrainRetrieverWithOpenSPGRetriever(RetrieverABC):
    def __init__(
        self,
        path_select: PathSelect = None,
        entity_linking: EntityLinking = None,
        llm: LLMClient = None,
        std_schema: StdSchema = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
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
        self.std_parser = get_std_logic_form_parser(std_schema, self.kag_project_config)

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        start_time = time.time()
        query = task.arguments.get("rewrite_query", task.arguments["query"])

        try:
            logical_node = task.arguments.get("logic_form_node", None)
            if not logical_node:
                return RetrieverOutput(
                    retriever_method=self.name,
                    err_msg="No logic node found in task arguments",
                )
            context = kwargs.get("context", Context())
            logical_node = std_logic_node(
                task_cache_id=self.kag_project_config.project_id,
                logic_node=logical_node,
                logic_parser=self.std_parser,
                context=context,
            )
            kg_graph = self.template.invoke(
                query=query,
                logic_nodes=[logical_node],
                graph_data=context.variables_graph,
                is_exact_match=True,
                name=self.name,
                **kwargs,
            )
            output = RetrieverOutput(retriever_method=self.name, graphs=[kg_graph])
        except Exception as e:
            logger.warning(f"{query} retriever with exception : {e}", exc_info=True)
            output = RetrieverOutput(
                retriever_method=self.name,
                err_msg=f"{task} {e}",
            )
        logger.debug(
            f"{self.name} `{query}`  Retrieved chunks num: {len(output.chunks)} cost={time.time() - start_time}"
        )
        return output

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
                    },
                },
                "required": ["query", "logic_form_node"],
            },
        }
