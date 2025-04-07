import logging
from typing import List, Optional

from tenacity import stop_after_attempt, retry

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.config import get_default_chat_llm_config
from kag.interface import PromptABC, LLMClient
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.reporter_abc import ReporterABC, DotRefresher
from kag.interface.solver.model.one_hop_graph import ChunkData, KgGraph
from kag.common.parser.logic_node_parser import GetSPONode
from kag.solver.utils import init_prompt_with_fallback
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.flow_component import (
    FlowComponent,
)
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_component.rc.rc_retriever import (
    RCRetrieverABC,
)
from kag.tools.algorithm_tool.chunk_retriever.ppr_chunk_retriever import (
    PprChunkRetriever,
)
from kag.tools.algorithm_tool.rerank.rerank_by_vector import RerankByVector

logger = logging.getLogger()


def get_history_qa(history: List[LogicNode]):
    history_qa = []
    for idx, lf in enumerate(history):
        if (
            lf.get_fl_node_result().summary != ""
            and "i don't know" not in lf.get_fl_node_result().summary.lower()
        ):
            history_qa.append(
                f"step{idx}:{lf.get_fl_node_result().sub_question}\nanswer:{lf.get_fl_node_result().summary}"
            )
    return history_qa


@FlowComponent.register("rc_open_spg", as_default=True)
class RCRetrieverOnOpenSPG(RCRetrieverABC):
    def __init__(
        self,
        top_k=10,
        ppr_chunk_retriever_tool: PprChunkRetriever = None,
        reranker: RerankByVector = None,
        llm_module: LLMClient = None,
        summary_prompt: PromptABC = None,
        rewrite_sub_query_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.ppr_chunk_retriever_tool = (
            ppr_chunk_retriever_tool
            or PprChunkRetriever.from_config(
                {
                    "type": "ppr_chunk_retriever",
                    "llm_module": get_default_chat_llm_config(),
                }
            )
        )
        self.reranker = reranker or RerankByVector.from_config(
            {
                "type": "rerank_by_vector",
            }
        )
        self.top_k = top_k
        self.summary_prompt = summary_prompt or init_prompt_with_fallback(
            "sub_question_summary", KAG_PROJECT_CONF.biz_scene
        )
        self.rewrite_sub_query_prompt = (
            rewrite_sub_query_prompt
            or init_prompt_with_fallback(
                "rewrite_sub_query", KAG_PROJECT_CONF.biz_scene
            )
        )

        self.solve_question_prompt = init_prompt_with_fallback(
            "solve_question", KAG_PROJECT_CONF.biz_scene
        )
        self.solve_question_without_docs_prompt = init_prompt_with_fallback(
            "solve_question_without_docs", KAG_PROJECT_CONF.biz_scene
        )
        self.solve_question_without_spo_prompt = init_prompt_with_fallback(
            "solve_question_without_spo", KAG_PROJECT_CONF.biz_scene
        )

    @retry(stop=stop_after_attempt(3))
    def generate_sub_answer(
        self, question: str, knowledge_graph: [], docs: [], history_qa=[], **kwargs
    ):
        """
        Generates a sub-answer based on the given question, knowledge graph, documents, and history.

        Parameters:
        question (str): The main question to answer.
        knowledge_graph (list): A list of knowledge graph data.
        docs (list): A list of documents related to the question.
        history (list, optional): A list of previous query-answer pairs. Defaults to an empty list.

        Returns:
        str: The generated sub-answer.
        """
        if knowledge_graph:
            if len(docs) > 0:
                prompt = self.solve_question_prompt
                params = {
                    "question": question,
                    "knowledge_graph": str(knowledge_graph),
                    "docs": [str(d) for d in docs],
                    "history": "\n".join(history_qa),
                }
            else:
                prompt = self.solve_question_without_docs_prompt
                params = {
                    "question": question,
                    "knowledge_graph": str(knowledge_graph),
                    "history": "\n".join(history_qa),
                }
        else:
            prompt = self.solve_question_without_spo_prompt
            params = {
                "question": question,
                "docs": [str(d) for d in docs],
                "history": "\n".join(history_qa),
            }
        llm_output = self.llm_module.invoke(
            params, prompt, with_json_parse=False, with_except=True, **kwargs
        )
        logger.debug(
            f"sub_question:{question}\n sub_answer:{llm_output} prompt:\n{prompt}"
        )
        if llm_output:
            return llm_output
        return "I don't know"

    def generate_summary(self, query, graph, chunks, history, **kwargs):
        if not chunks:
            return ""
        history_qa = get_history_qa(history)
        return self.generate_sub_answer(
            question=query, knowledge_graph=graph, docs=chunks, history_qa=history_qa, **kwargs
        )

    def _rewrite_sub_query_with_history_qa(
        self, history: List[LogicNode], sub_query, reporter, tag_name
    ):
        if history:
            history_qa = get_history_qa(history)
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
                segment_name="thinker",
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

    def invoke(
        self, query, logic_nodes: List[LogicNode], graph_data: KgGraph, **kwargs
    ) -> List[ChunkData]:
        component_name = self.name
        reporter: Optional[ReporterABC] = kwargs.get("reporter", None)
        sub_queries = []
        sub_chunks = []
        used_lf = []
        logger.info(f"Starting invoke method with query: {query}")
        for logic_node in logic_nodes:
            if not isinstance(logic_node, GetSPONode):
                continue
            if logic_node.get_fl_node_result().summary:
                used_lf.append(logic_node)
                continue
            # Start processing a new logic node
            logger.info(
                f"`{query}` Processing logic node with sub-query: {logic_node.sub_query}"
            )
            dot_refresh = DotRefresher(reporter=reporter, segment=kwargs.get("segment_name", "thinker"),
                                       tag_name=f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                                       content="executing", params={
                    "component_name": component_name
                })

            if reporter:
                reporter.add_report_line(
                    kwargs.get("segment_name", "thinker"),
                    f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                    logic_node.sub_query,
                    "INIT",
                    component_name=component_name
                )
                reporter.add_report_line(
                    kwargs.get("segment_name", "thinker"),
                    f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                    "executing",
                    "RUNNING",
                    component_name=component_name
                )
                dot_refresh.start()
            try:
                rewrite_queries = self._rewrite_sub_query_with_history_qa(
                    history=used_lf,
                    sub_query=logic_node.sub_query,
                    reporter=reporter,
                    tag_name=f"rc_retriever_rewrite_{logic_node.sub_query}",
                )
                logger.info(f"`{query}` Rewritten queries: {rewrite_queries}")
                entities = []
                selected_rel = []
                if graph_data is not None:
                    s_entities = graph_data.get_entity_by_alias(logic_node.s.alias_name)
                    if s_entities:
                        entities.extend(s_entities)
                    o_entities = graph_data.get_entity_by_alias(logic_node.o.alias_name)
                    if o_entities:
                        entities.extend(o_entities)
                    selected_rel = graph_data.get_all_spo()
                chunks, match_spo = self.ppr_chunk_retriever_tool.invoke(
                    queries=[query] + rewrite_queries,
                    start_entities=entities,
                    top_k=self.top_k,
                )
                logger.info(f"`{query}`  Retrieved chunks num: {len(chunks)}")
                if reporter:
                    dot_refresh.stop()
                    reporter.add_report_line(
                        kwargs.get("segment_name", "thinker"),
                        f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                        "finish",
                        "FINISH",
                        component_name=component_name,
                        chunk_num = len(chunks),
                        nodes_num = len(entities),
                        edges_num = len(selected_rel),
                        desc="retrieved_info_digest"
                    )

                    matched_graph = match_spo + selected_rel
                    reporter.add_report_line(
                        kwargs.get("segment_name", "thinker"),
                        f"end_sub_kag_retriever_{logic_node.sub_query}",
                        matched_graph if matched_graph else "finish",
                        "FINISH",
                    )


                summary = self.generate_summary(
                    query=logic_node.sub_query,
                    graph=logic_node.get_fl_node_result().spo,
                    chunks=chunks,
                    history=used_lf,
                    reporter=reporter,
                    segment_name=kwargs.get("segment_name", "thinker"),
                    tag_name=f"rc_retriever_summary_{logic_node.sub_query}",
                )
                logger.info(f"`{query}` subq: {logic_node.sub_query} answer:{summary}")
                logic_node.get_fl_node_result().summary = summary
                if summary and "i don't know" not in summary.lower():
                    graph_data.add_answered_alias(logic_node.s.alias_name.alias_name, summary)
                    graph_data.add_answered_alias(logic_node.p.alias_name.alias_name, summary)
                    graph_data.add_answered_alias(logic_node.o.alias_name.alias_name, summary)

                logic_node.get_fl_node_result().sub_question = rewrite_queries
                logic_node.get_fl_node_result().chunks = chunks
                sub_queries += rewrite_queries
                sub_chunks.append(chunks)
                used_lf.append(logic_node)
            except Exception as e:
                if reporter:
                    dot_refresh.stop()
                    reporter.add_report_line(
                        kwargs.get("segment_name", "thinker"),
                        f"begin_sub_kag_retriever_{logic_node.sub_query}_{component_name}",
                        f"failed: reason={e}",
                        "ERROR",
                        component_name=component_name
                    )
                logger.error(f"`{query}` subq: {logic_node.sub_query} error:{e}", exc_info=True)

        return self.reranker.invoke(
            query=query, sub_queries=sub_queries, sub_question_chunks=sub_chunks
        )

    def is_break(self):
        return self.break_flag

    def break_judge(self, logic_nodes: List[LogicNode], **kwargs):
        self.break_flag = False
