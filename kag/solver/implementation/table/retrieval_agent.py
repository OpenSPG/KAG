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
        # ner_query = f"{self.init_question}；子问题：{query}"
        ner_query = query
        entities = self.chunk_retriever.named_entity_recognition(query=ner_query)
        all_entities = set()
        for entity in entities:
            all_entities.add(entity["entity"])
            for i, alias in enumerate(entity["alias"]):
                if i <= 1:
                    all_entities.add(alias)

        entities = list(all_entities)

        recall_rst = []
        kg_entities, _ = self.chunk_retriever.match_table_mertric_constraint(
            entities, top_k=10
        )

        # table recall
        if len(kg_entities) > 0:
            tables = self.chunk_retriever.retrieval_table_metric_by_vector(
                self.question, query_type="Table", top_k=1
            )
            tables = {
                table["node"]["name"]: table["node"]["content"]
                for table in tables
                if "name" in table["node"] and "content" in table["node"]
            }
            table_chunk_list = self.chunk_retriever.retrieval_table_metric_by_page_rank(
                entities=kg_entities, topk=1, target_type="Table"
            )
            table_chunk_list = {d["name"]: d["content"] for d in table_chunk_list}
            table_value_list = []
            for k, v in tables.items():
                table_value_list.append(f"# {k}\n{v}")
            for k, v in table_chunk_list.items():
                table_value_list.append(f"# {k}\n{v}")
            recall_rst.extend(table_value_list)

        # table metrics recall
        if len(kg_entities) > 0:
            table_metrics_list1 = self.chunk_retriever.retrieval_table_metric_by_vector(
                self.question, query_type="TableMetric", top_k=10
            )
            table_metrics_list1 = [node["node"] for node in table_metrics_list1]
            table_metrics_list2 = self.chunk_retriever.get_table_metrics_by_entities(
                entities=kg_entities, topk=10
            )
            table_metrics_list = table_metrics_list1 + table_metrics_list2
            table_metrics_list = [mertic["name"] for mertic in table_metrics_list]
            recall_rst.extend(table_metrics_list)

        # recall from docs
        docs_with_score = self.chunk_retriever.recall_docs(query=query, top_k=5)
        docs = ["#".join(item.split("#")[:-1]) for item in docs_with_score]
        recall_rst.extend(docs)

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
        row_docs = self.recall_docs(query=self.question)
        print(f"rowdocs,query={self.question}\n{row_docs}")
        rerank_docs = self.rerank_docs(queries=[], passages=row_docs)
        print(f"rerank,query={self.question}\n{rerank_docs}")
        docs = "\n\n".join(rerank_docs)
        llm: LLMClient = self.llm_module
        answer = llm.invoke(
            {"docs": docs, "question": self.question},
            self.sub_question_answer,
            with_except=True,
        )
        if "i don't know" in answer.lower():
            # 尝试使用原始召回数据再回答一次
            docs = "\n\n".join(row_docs)
            llm: LLMClient = self.llm_module
            answer = llm.invoke(
                {"docs": docs, "question": self.question},
                self.sub_question_answer,
                with_except=True,
            )
        return answer, rerank_docs

    def get_sub_item_reall(self, entities):
        index = self.question.find("的所有子项")
        if index < 0:
            return None
        for entity in entities:
            index2 = self.question.find(entity)
            if index2 > 0 and index2 < index and len(entity) == (index - index2):
                return entity
        return None
