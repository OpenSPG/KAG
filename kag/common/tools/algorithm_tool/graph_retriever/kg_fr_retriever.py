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


from kag.common.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import (
    PprChunkRetriever,
)
from kag.common.tools.algorithm_tool.graph_retriever.entity_linking import EntityLinking
from kag.common.tools.algorithm_tool.graph_retriever.path_select.path_select import (
    PathSelect,
)

logger = logging.getLogger()


@RetrieverABC.register("kg_fr_open_spg")
class KgFreeRetrieverWithOpenSPGRetriever(RetrieverABC):
    def __init__(
        self,
        path_select: PathSelect = None,
        entity_linking: EntityLinking = None,
        llm: LLMClient = None,
        ppr_chunk_retriever_tool: RetrieverABC = None,
        std_schema: StdSchema = None,
        top_k=10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm or LLMClient.from_config(get_default_chat_llm_config())
        self.path_select = path_select or PathSelect.from_config(
            {"type": "fuzzy_one_hop_select"}
        )
        if isinstance(entity_linking, dict):
            entity_linking = EntityLinking.from_config(entity_linking)
        self.entity_linking = entity_linking or EntityLinking.from_config(
            {
                "type": "default_entity_linking",
                "recognition_threshold": 0.8,
                "exclude_types": ["Chunk"],
            }
        )
        self.template = KgRetrieverTemplate(
            path_select=self.path_select,
            entity_linking=self.entity_linking,
            llm_module=self.llm,
        )
        self.ppr_chunk_retriever_tool = (
            ppr_chunk_retriever_tool
            or PprChunkRetriever.from_config(
                {
                    "type": "ppr_chunk_retriever",
                    "llm_client": get_default_chat_llm_config(),
                }
            )
        )
        self.top_k = top_k
        self.std_parser = get_std_logic_form_parser(std_schema, self.kag_project_config)

    def invoke(self, task, **kwargs) -> RetrieverOutput:
        try:
            query = task.arguments.get("rewrite_query", task.arguments["query"])
            logical_node = task.arguments.get("logic_form_node", None)
            if not logical_node:
                return RetrieverOutput(
                    retriever_method=self.name,
                    err_msg="No logical-form node found",
                )
            context = kwargs.get("context", Context())
            logical_node = std_logic_node(
                task_cache_id=self.kag_project_config.project_id,
                logic_node=logical_node,
                logic_parser=self.std_parser,
                context=context,
            )
            graph_data = self.template.invoke(
                query=query,
                logic_nodes=[logical_node],
                graph_data=context.variables_graph,
                is_exact_match=True,
                name=self.name,
                **kwargs,
            )

            entities = []
            # selected_rel = []
            if graph_data is not None:
                s_entities = graph_data.get_entity_by_alias_without_attr(
                    logical_node.s.alias_name
                )
                if s_entities:
                    entities.extend(s_entities)
                o_entities = graph_data.get_entity_by_alias_without_attr(
                    logical_node.o.alias_name
                )
                if o_entities:
                    entities.extend(o_entities)
                entities = list(set(entities))

            start_time = time.time()
            output: RetrieverOutput = self.ppr_chunk_retriever_tool.invoke(
                task=task,
                start_entities=entities,
                top_k=self.top_k,
            )

            logger.info(
                f"`{query}`  Retrieved chunks num: {len(output.chunks)} cost={time.time() - start_time}"
            )
            output.graphs = [graph_data]
            output.retriever_method = self.name
            return output
        except Exception as e:
            logger.error(e, exc_info=True)
            return RetrieverOutput(
                retriever_method=self.name,
                err_msg=f"{task} {e}",
            )

    def schema(self):
        return {
            "name": "kg_fr_retriever",
            "description": "Retrieve graph data in knowledge graph fr level",
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
