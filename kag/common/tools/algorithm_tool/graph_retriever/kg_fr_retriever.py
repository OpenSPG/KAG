import logging
import time
from typing import List, Optional

from kag.common.config import get_default_chat_llm_config
from kag.common.tools.algorithm_tool.graph_retriever.lf_kg_retriever_template import KgRetrieverTemplate
from kag.interface import LLMClient, RetrieverABC, RetrieverOutput, Context
from kag.interface.solver.reporter_abc import ReporterABC

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
        entity_linking: EntityLinking =None,
        llm: LLMClient = None,
        ppr_chunk_retriever_tool: RetrieverABC = None,
        top_k=10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = kwargs.get("name", "kg_fr")
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

    def invoke(self, task, **kwargs) -> RetrieverOutput:

        query = task.arguments.get(
            "rewrite_query", task.arguments["query"]
        )
        logical_node = task.arguments.get("logic_form_node", None)
        if not logical_node:
            return RetrieverOutput(
                retriever_method=self.schema().get("name", ""),
                err_msg="No logical-form node found",
            )
        context = kwargs.get("context", Context())


        graph_data = self.template.invoke(
            query=query,
            logic_nodes=[logical_node],
            graph_data=context.variables_graph,
            is_exact_match=True,
            name=self.name,
            **kwargs
        )


        entities = []
        selected_rel = []
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
        output.retriever_method = self.schema().get("name", "")
        return output

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
                    }
                },
                "required": ["query", "logic_form_node"],
            },
        }