# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
# flake8: noqa
from typing import Dict

from kag.common.registry import Registrable


class KAGIndexManager(Registrable):
    def __init__(self, llm_config: Dict, vectorize_model_config: Dict):
        self.extractor_config = self.build_extractor_config(
            llm_config, vectorize_model_config
        )
        self.retriever_config = self.build_retriever_config(
            llm_config, vectorize_model_config
        )

    @property
    def name(self):
        return "KAG Index Manager"

    @property
    def description(self) -> str:
        return ""

    @property
    def schema(self) -> str:
        return ""

    @property
    def as_default(self) -> bool:
        return False

    def get_meta(self):
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "config": {
                "extractor": self.extractor_config,
                "retriever": self.retriever_config,
            },
            "index_cost": self.index_cost,
            "retrieval_method": self.retrieval_method,
            "applicable_scenarios": self.applicable_scenarios,
            "as_default": self.as_default,
        }

    @property
    def applicable_scenarios(self) -> str:
        return ""

    @property
    def index_cost(self) -> str:
        return ""

    @property
    def retrieval_method(self) -> str:
        return ""

    def build_extractor_config(self, llm_config: Dict, vectorize_model_config: Dict):
        return []

    def build_retriever_config(self, llm_config: Dict, vectorize_model_config: Dict):
        return []


@KAGIndexManager.register("atomic_query_index")
class AtomicIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Atomic Query based Index Manager"

    @property
    def schema(self) -> str:
        return """
AtomicQuery(原子问): EntityType
  properties:
    content(内容): Text
      index: TextAndVector
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B 121535 tokens
        2、耗时：109.5 秒
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：
        
        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))
        
        # recall_atomic_questions, 基于question title，通过bm25/emb 等实现atomic question召回
        # get_qa_associate_chunks, 基于chunk 与 question 的关联，实现chunk召回
        chunks2 = get_qa_associate_chunks(recall_atomic_question(rewrite(sub_query)))
        
        # recall_summary, 基于summary title，通过bm25/emb 等实现summary召回
        # get_summary_associate_chunks, 基于chunk 与summary 的关联实现chunk召回
        chunks3 = get_summary_associate_chunks(recall_summary(rewrite(sub_query)))
        
        # recall_outline，基于outline title, 通过bm25/emb 等实现outline召回
        # recall_outline, 基于outline_childOf->outline, 实现outline 扩展召回
        # get_outline_associate_chunks, 基于chunk 与 summary 关联实现chunk 召回
        chunks4 = get_outline_associate_chunks(recall_outline(rewrite(sub_query)))
        
        # recall_table，基于table title, 通过bm25/emb 等实现table召回
        # get_table_associate_chunks, 基于chunk 与 table 关联实现chunk 召回
        chunks5 = get_table_associate_chunks(recall_table(rewrite(sub_query)))
        
        ……
        return [chunks1,chunks2,chunks3,chunks4, chunks5,…]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return "通过构建原子问，实现原子问的检索，一般用于检索与原子问相关的chunk"

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "atomic_query_extractor",
                "llm": llm_config,
                "prompt": {"type": "atomic_query_extract"},
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "atomic_query_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "llm_client": llm_config,
                "query_rewrite_prompt": {"type": "atomic_query_rewrite_prompt"},
                "search_api": {"type": "openspg_search_api"},
                "graph_api": {"type": "openspg_graph_api"},
                "top_k": 10,
            },
            {
                "type": "vector_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "top_k": 10,
            },
            {
                "type": "text_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "top_k": 10,
            },
        ]


@KAGIndexManager.register("chunk_index")
class ChunkIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Chunk based Index Manager"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): EntityType
     properties:
        content(内容): Text
          index: TextAndVector        
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B xx tokens
        2、向量模型消耗：bge-m3 xx tokens
        3、耗时：xx 分钟
        4、存储：xx GB
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：

        基础索引，适用性广，一般场景都可以使用。Chunk 索引一般不允许用户变更。
        

        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))

        # recall_atomic_questions, 基于question title，通过bm25/emb 等实现atomic question召回
        # get_qa_associate_chunks, 基于chunk 与 question 的关联，实现chunk召回
        chunks2 = get_qa_associate_chunks(recall_atomic_question(rewrite(sub_query)))

        # recall_summary, 基于summary title，通过bm25/emb 等实现summary召回
        # get_summary_associate_chunks, 基于chunk 与summary 的关联实现chunk召回
        chunks3 = get_summary_associate_chunks(recall_summary(rewrite(sub_query)))

        # recall_outline，基于outline title, 通过bm25/emb 等实现outline召回
        # recall_outline, 基于outline_childOf->outline, 实现outline 扩展召回
        # get_outline_associate_chunks, 基于chunk 与 summary 关联实现chunk 召回
        chunks4 = get_outline_associate_chunks(recall_outline(rewrite(sub_query)))

        # recall_diagram，基于diagram title, 通过bm25/emb 等实现diagram召回
        # get_diagram_associate_chunks, 基于chunk 与 diagram 关联实现chunk 召回
        chunks5 = get_diagram_associate_chunks(recall_diagram(rewrite(sub_query)))

        ……

        return [chunks1,chunks2,chunks3,chunks4, chunks5,…]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return ""

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "naive_rag_extractor",
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "vector_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "top_k": 10,
            },
            {
                "type": "text_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "top_k": 10,
            },
        ]


@KAGIndexManager.register("table_index")
class TableIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Table based Index Manager"

    @property
    def schema(self) -> str:
        return """
Table(表格): EntityType
    properties:
        content(内容): Text
          index: TextAndVector
        beforeText(前缀): Text
          index: TextAndVector
        afterText(后缀): Text
          index: TextAndVector
    relations:
        sourceChunk(关联): Chunk       
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B xx tokens
        2、向量模型消耗：bge-m3 xx tokens
        3、耗时：xx 分钟
        4、存储：xx GB
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：
        
        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))
        ……
        return [chunks1]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return "通过构建表格索引，实现表格的检索"

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "table_extractor",
                "llm": llm_config,
                "table_context_prompt": {"type": "table_context"},
                "table_row_col_summary_prompt": {"type": "table_row_col_summary"},
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "table_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "graph_api": {"type": "openspg_graph_api"},
                "top_k": 10,
            },
        ]


@KAGIndexManager.register("summary_index")
class SummaryIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Summary based Index Manager"

    @property
    def schema(self) -> str:
        return """
Summary(文本摘要): EntityType
     properties:
        content(内容): Text
          index: TextAndVector
     relations:
        sourceChunk(关联): Chunk
        childOf(子摘要): Summary      
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B 88701 tokens
        2、耗时：85.2 秒钟
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：
        
        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))
        ……
        return [chunks1]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return "通过大模型总结的摘要，实现摘要的检索，一般用于检索与摘要相关的chunk"

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "summary_extractor",
                "llm_module": llm_config,
                "chunk_summary_prompt": {"type": "default_chunk_summary"},
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "summary_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "graph_api": {"type": "openspg_graph_api"},
                "top_k": 10,
                "score_threshold": 0.8,
            },
        ]


@KAGIndexManager.register("outline_index")
class OutlineIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Outline based Index Manager"

    @property
    def schema(self) -> str:
        return """
Outline(标题大纲): EntityType
     properties:
        content(内容): Text
          index: TextAndVector
     relations:
        sourceChunk(关联): Chunk
        childOf(子标题): Outline     
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B xx tokens
        2、向量模型消耗：bge-m3 xx tokens
        3、耗时：xx 分钟
        4、存储：xx GB
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：
        
        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))
        ……
        return [chunks1]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return "通过构建时文本的大纲，实现大纲的检索，一般用于检索与大纲相关的chunk"

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "outline_extractor",
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "outline_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {"type": "openspg_search_api"},
                "graph_api": {"type": "openspg_graph_api"},
                "top_k": 10,
            },
        ]


@KAGIndexManager.register("kag_hybrid_index")
class KAGHybridIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "Chunk and Graph based hybrid Index Manager"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): EntityType
     properties:
        content(内容): Text
          index: TextAndVector        
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B xx tokens
        2、向量模型消耗：bge-m3 xx tokens
        3、耗时：xx 分钟
        4、存储：xx GB
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        msg = """
        检索方法描述：
        
        # recall_chunks,基于chunk name/content, 通过bm25/emb 等实现chunk召回
        chunks1 = recall_chunks(rewrite(sub_query))
        return [chunks1]
        """
        return msg

    @property
    def retrieval_method(self) -> str:
        return "通过构建chunk 与 图谱的关联，实现chunk 的检索，一般用于检索与图谱相关的chunk"

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "schema_free_extractor",
                "llm": llm_config,
            }
        ]

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return [
            {
                "type": "kg_cs_open_spg",
                "path_select": {
                    "type": "exact_one_hop_select",
                    "vectorize_model": vectorize_model_config,
                },
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.9,
                    "exclude_types": ["Chunk"],
                    "vectorize_model": vectorize_model_config,
                },
                "llm": llm_config,
            },
            {
                "type": "kg_fr_open_spg",
                "top_k": 20,
                "path_select": {
                    "type": "fuzzy_one_hop_select",
                    "llm_client": llm_config,
                    "vectorize_model": vectorize_model_config,
                },
                "ppr_chunk_retriever_tool": {
                    "type": "ppr_chunk_retriever",
                    "llm_client": llm_config,
                    "vectorize_model": vectorize_model_config,
                },
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.8,
                    "exclude_types": ["Chunk"],
                    "vectorize_model": vectorize_model_config,
                },
                "llm": llm_config,
            },
            {
                "type": "rc_open_spg",
                "vector_chunk_retriever": {
                    "type": "vector_chunk_retriever",
                    "vectorize_model": vectorize_model_config,
                },
                "vectorize_model": vectorize_model_config,
                "top_k": 20,
            },
        ]
