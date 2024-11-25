#!/usr/bin/python
# encoding: utf-8
"""
Project: openspgapp
Auther: Zhongpu Bo
Email: zhongpubo.bzp@antgroup.com
DateTime: 2024/11/17 20:57
Description: 

"""

from typing import List

from kag.common.llm.client.llm_client import LLMClient
from kag.common.vectorizer.vectorizer import Vectorizer
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface.retriever.chunk_retriever_abc import ChunkRetrieverABC


class Neo4JRetriever(ChunkRetrieverABC):
    """
    KAGRetriever class for retrieving and processing knowledge graph data from a graph database.

    this retriever references the implementation of Hippoag for the combination of dpr & ppr, developer can define your Retriever

    Parameters:
    - project_id (str, optional): Project ID to load specific project configurations.

    """

    graph_store_config = {
        "uri": "",
        "user": "",
        "password": "",
    }

    vec_conf = {
        "vectorizer": "knext.common.vectorizer.LocalVectorizer",
        "path": "~/.cache/vectorizer/BAAI/bge-base-en-v1.5",
    }

    model = {
    }

    def __init__(self, method, **kwargs):
        self.client = LLMClient.from_config(self.model)
        self.method = method
        if "database" in kwargs:
            self.graph_store_config['database'] = kwargs['database']
        self.graph_store = Neo4jClient(
            init_type="read",
            **self.graph_store_config
        )
        self.graph_store.vectorizer = Vectorizer.from_config(self.vec_conf)

    def rerank_docs(self, queries: List[str], passages: List[str]) -> List[str]:
        return passages

    def recall_docs(self, query: str, top_k: int = 5, **kwargs) -> List[str]:
        if self.method == 'BM25':
            res = self.graph_store.text_search(
                label_constraints='Chunk',
                query_string=query,
                topk=top_k
            )
        elif self.method == 'BGE':
            res = self.graph_store.vector_search(
                label='Chunk',
                property_key='content',
                query_text_or_vector=query,
                topk=top_k
            )
        else:
            raise ValueError

        docs = [
                   "{doc}#{score}".format(doc=r['node']['content'], score=r["score"])
                   for r in sorted(res, key=lambda x: x['score'], reverse=True)
               ][:top_k]
        return docs
