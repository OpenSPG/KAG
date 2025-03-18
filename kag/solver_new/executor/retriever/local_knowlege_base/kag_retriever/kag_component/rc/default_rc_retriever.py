from typing import List

from kag.common.conf import KAG_CONFIG
from kag.interface.solver.base_model import LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import ChunkData, KgGraph
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.flow_component import \
    FlowComponent
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.rc.rc_retriever import \
    RCRetrieverABC
from kag.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import PprChunkRetriever
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@FlowComponent.register("rc_open_spg", as_default=True)
class RCRetrieverOnOpenSPG(RCRetrieverABC):
    def __init__(self, top_k=10, ppr_chunk_retriever_tool: PprChunkRetriever=None, reranker: RerankByVector=None, **kwargs):
        super().__init__(**kwargs)
        self.ppr_chunk_retriever_tool = ppr_chunk_retriever_tool or PprChunkRetriever.from_config({
            "type": "ppr_chunk_retriever",
            "llm_module": KAG_CONFIG.all_config["openie_llm"]
        })
        self.reranker = reranker or RerankByVector.from_config({
            "type": "rerank_by_vector",
        })
        self.top_k = top_k

    def invoke(self, query, logic_nodes: List[LogicNode], graph_data: KgGraph, **kwargs) -> List[ChunkData]:
        sub_queries = []
        sub_chunks = []
        for logic_node in logic_nodes:
            if not isinstance(logic_node, GetSPONode):
                continue
            entities = []
            if graph_data is not None:
                s_entities = graph_data.get_entity_by_alias(logic_node.s.alias_name)
                if s_entities:
                    entities.extend(s_entities)
                o_entities = graph_data.get_entity_by_alias(logic_node.o.alias_name)
                if o_entities:
                    entities.extend(o_entities)
            chunks = self.ppr_chunk_retriever_tool.invoke(
                queries=[logic_node.sub_query], start_entities=entities, top_k=self.top_k
            )
            logic_node.get_fl_node_result().chunks = chunks
            sub_queries.append(logic_node.sub_query)
            sub_chunks.append(chunks)
        return self.reranker.invoke(query=query, sub_queries=sub_queries, sub_question_chunks=sub_chunks)


    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False