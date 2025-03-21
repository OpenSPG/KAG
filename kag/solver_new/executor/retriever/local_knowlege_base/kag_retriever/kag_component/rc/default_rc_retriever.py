from typing import List, Optional

from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF
from kag.interface import PromptABC, LLMClient
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.reporter_abc import ReporterABC
from kag.solver.logic.core_modules.common.one_hop_graph import ChunkData, KgGraph
from kag.solver.logic.core_modules.parser.logic_node_parser import GetSPONode
from kag.solver.utils import init_prompt_with_fallback
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.flow_component import \
    FlowComponent
from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_component.rc.rc_retriever import \
    RCRetrieverABC
from kag.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import PprChunkRetriever
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector


@FlowComponent.register("rc_open_spg", as_default=True)
class RCRetrieverOnOpenSPG(RCRetrieverABC):
    def __init__(self, top_k=10, ppr_chunk_retriever_tool: PprChunkRetriever = None,
                 reranker: RerankByVector = None,
                 llm_module: LLMClient = None,
                 summary_prompt: PromptABC = None,
                 rewrite_sub_query_prompt: PromptABC = None, **kwargs):
        super().__init__(**kwargs)
        self.llm_module = llm_module or LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
        self.ppr_chunk_retriever_tool = ppr_chunk_retriever_tool or PprChunkRetriever.from_config({
            "type": "ppr_chunk_retriever",
            "llm_module": KAG_CONFIG.all_config["chat_llm"]
        })
        self.reranker = reranker or RerankByVector.from_config({
            "type": "rerank_by_vector",
        })
        self.top_k = top_k
        self.summary_prompt = summary_prompt or init_prompt_with_fallback("sub_question_summary",
                                                                          KAG_PROJECT_CONF.biz_scene)
        self.rewrite_sub_query_prompt = rewrite_sub_query_prompt or init_prompt_with_fallback(
            "rewrite_sub_query", KAG_PROJECT_CONF.biz_scene
        )

    def generate_summary(self, query, graph, chunks, history, **kwargs):
        if not chunks:
            return ""
        history_qa = self.get_history_qa(history)
        return self.llm_module.invoke({
            "history": history_qa,
            "knowledge_graph": str(graph),
            "question": query,
            "docs": chunks
        }, self.summary_prompt,
            reporter=kwargs.get("reporter", None),
            tag_name=kwargs.get("tag_name", None),
            segment_name="thinker")

    def get_history_qa(self, history: List[LogicNode]):
        history_qa = []
        for idx, lf in enumerate(history):
            if lf.get_fl_node_result().summary != "":
                history_qa.append(
                    f"step{idx}:{lf.get_fl_node_result().sub_question}\nanswer:{lf.get_fl_node_result().summary}"
                )
        return history_qa

    def _rewrite_sub_query_with_history_qa(self, history: List[LogicNode], sub_query, reporter, tag_name):
        if history:
            history_qa = self.get_history_qa(history)
            sub_query_rewrite = []

            sub_query_rewrite_l = self.llm_module.invoke(
                {
                    "history_qa": "\n".join(history_qa),
                    "question": sub_query,
                },
                self.rewrite_sub_query_prompt,
                with_json_parse=False,
                reporter=reporter,
                tag_name=tag_name,
                segment_name="thinker"
            )
            if isinstance(sub_query_rewrite_l, list):
                sub_query_rewrite = []
                for sub_query_rewrite_i in sub_query_rewrite_l:
                    sub_query_rewrite.append(
                        sub_query_rewrite_i
                        if sub_query_rewrite_i
                           and sub_query_rewrite_i.lower() not in ["[]", "i don't know"]
                        else sub_query
                    )
            elif isinstance(sub_query_rewrite_l, str):
                sub_query_rewrite = [
                    (
                        sub_query_rewrite_l
                        if sub_query_rewrite_l
                           and sub_query_rewrite_l.lower() not in ["[]", "i don't know"]
                        else sub_query
                    )
                ]
            return_query = []
            for q in sub_query_rewrite:
                if q == "" or q is None:
                    continue
                return_query.append(q)
            if len(return_query) == 0:
                return_query = [sub_query]
            return return_query
        else:
            return [sub_query]

    def invoke(self, query, logic_nodes: List[LogicNode], graph_data: KgGraph, **kwargs) -> List[ChunkData]:
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        sub_queries = []
        sub_chunks = []
        used_lf = []
        for logic_node in logic_nodes:
            if not isinstance(logic_node, GetSPONode):
                continue
            if logic_node.get_fl_node_result().summary:
                used_lf.append(logic_node)
                continue
            if reporter:
                reporter.add_report_line(
                    "thinker",
                    f"rc_retriever_begin_{logic_node.sub_query}",
                    logic_node.sub_query,
                    "FINISH",
                )
            rewrite_queries = self._rewrite_sub_query_with_history_qa(history=used_lf, sub_query=logic_node.sub_query,
                                                                      reporter=reporter,
                                                                      tag_name=f"rc_retriever_rewrite_{logic_node.sub_query}")
            entities = []
            if graph_data is not None:
                s_entities = graph_data.get_entity_by_alias(logic_node.s.alias_name)
                if s_entities:
                    entities.extend(s_entities)
                o_entities = graph_data.get_entity_by_alias(logic_node.o.alias_name)
                if o_entities:
                    entities.extend(o_entities)
            chunks = self.ppr_chunk_retriever_tool.invoke(
                queries=[query] + rewrite_queries, start_entities=entities, top_k=self.top_k
            )
            if reporter:
                reporter.add_report_line(
                    "thinker",
                    f"rc_retriever_end_{logic_node.sub_query}",
                    len(chunks),
                    "FINISH",
                )
            # summary
            summary = self.generate_summary(query=rewrite_queries, graph=logic_node.get_fl_node_result().spo,
                                            chunks=chunks, history=used_lf, reporter=reporter,
                                            tag_name=f"rc_retriever_summary_{logic_node.sub_query}")
            logic_node.get_fl_node_result().summary = summary
            logic_node.get_fl_node_result().sub_question = rewrite_queries
            logic_node.get_fl_node_result().chunks = chunks
            sub_queries += rewrite_queries
            sub_chunks.append(chunks)
            used_lf.append(logic_node)

        return self.reranker.invoke(query=query, sub_queries=sub_queries, sub_question_chunks=sub_chunks)

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
