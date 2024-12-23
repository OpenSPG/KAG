from typing import List

from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC
from kag.solver.implementation.table.search_tree import SearchTree, SearchTreeNode
from kag.common.retriever.kag_retriever import DefaultRetriever
from kag.common.llm.client import LLMClient
from kag.common.base.prompt_op import PromptOp


class RetrievalAgent(ChunkRetrieverABC):
    def __init__(self, init_question, question, **kwargs):
        super().__init__(**kwargs)
        self.init_question = init_question
        self.question = question
        self.history = SearchTree(question)
        self.chunk_retriever = DefaultRetriever(**kwargs)

        self.sub_question_answer = PromptOp.load(self.biz_scene, "sub_question_answer")(
            language=self.language
        )

        self.select_docs = PromptOp.load(self.biz_scene, "select_docs")(
            language=self.language
        )

    def recall_docs(self, query: str, top_k: int = 5, **kwargs) -> List[str]:
        entities = self.chunk_retriever.named_entity_recognition(query=query)
        parent_entity = self.get_sub_item_reall(entities=entities)

        recall_rst = []
        kg_entities, _ = self.chunk_retriever.match_table_mertric_constraint(
            entities, top_k=100
        )

        # table recall
        if len(kg_entities) > 0:
            table_chunk_list = self.chunk_retriever.retrieval_table_metric_by_page_rank(
                entities=kg_entities, topk=2, target_type="Table"
            )
            table_chunk_list = [d["content"] for d in table_chunk_list]
            recall_rst.extend(table_chunk_list)

        # table metrics recall
        if len(kg_entities) > 0:
            table_metrics_list = self.chunk_retriever.get_table_metrics_by_entities(
                entities=kg_entities, topk=20
            )
            table_metrics_list = [mertic["name"] for mertic in table_metrics_list]
            recall_rst.extend(table_metrics_list)

        # recall from docs
        docs_with_score = self.chunk_retriever.recall_docs(query=query, top_k=5)
        docs = ["#".join(item.split("#")[:-1]) for item in docs_with_score]
        recall_rst.extend(docs)

        # subitem recall
        if parent_entity is not None:
            self.sub_item_recall(parent_entity=parent_entity)

        return recall_rst

    def rerank_docs(self, queries: List[str], passages: List[str]) -> List[str]:
        docs = "\n\n".join(passages)
        llm: LLMClient = self.llm_module
        return llm.invoke(
            {"docs": docs, "question": self.question},
            self.select_docs,
            with_except=True,
        )

    def answer(self):
        docs = self.recall_docs(query=self.question)
        docs = self.rerank_docs(queries=[], passages=docs)
        llm: LLMClient = self.llm_module
        answer = llm.invoke(
            {"docs": docs, "question": self.question},
            self.sub_question_answer,
            with_except=True,
        )
        return answer, docs

    def get_sub_item_reall(self, entities):
        index = self.question.find("的所有子项")
        if index < 0:
            return None
        for entity in entities:
            entity = entity["name"]
            index2 = self.question.find(entity)
            if index2 > 0 and index2 < index and len(entity) == (index - index2):
                return entity
        return None

    def sub_item_recall(self, parent_entity):
        kg_entities, _ = self.chunk_retriever.match_table_mertric_constraint(
            parent_entity, top_k=1
        )
        # TODO 查询子项目

        return ""
