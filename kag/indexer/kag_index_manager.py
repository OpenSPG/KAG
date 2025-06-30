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

from kag.common.conf import KAGConstants
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
        return "通过构建原子问，实现原子问的检索，一般用于检索与原子问相关的chunk"

    def build_extractor_config(
        self, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        return []

    def build_retriever_config(
        self, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        return []


@KAGIndexManager.register("atomic_query_index")
class AtomicIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于原子查询的索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器通过从文档中抽取独立的、可回答的原子查询（AtomicQuery）来构建索引。它旨在将复杂问题分解，并通过检索与这些原子问题最相关的文本块（Chunk）来提供精确的上下文，特别适用于需要细粒度问答的场景。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector
AtomicQuery(原子问): IndexType
  properties:
    title(标题): Text
      index: TextAndVector
  relations:
    sourceChunk(关联文本块): Chunk
    similar(相似问题): AtomicQuery  
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
        return """
        **适用场景**: 适用于事实问答、FAQ等可以通过简单问句精确匹配找到答案的场景。

        **检索流程**:
        1. `rewrite(sub_query)`: 对用户问题进行重写，使其更规范。
        2. `recall_atomic_question(...)`: 基于重写后的问题，通过语义或文本匹配召回相似的原子问题。
        3. `get_qa_associate_chunks(...)`: 根据召回的原子问题，找到与之关联的文本块作为最终答案来源。
        
        **代码示例**:
        `chunks = get_qa_associate_chunks(recall_atomic_question(rewrite(sub_query)))`
        """

    @property
    def retrieval_method(self) -> str:
        return "通过构建原子问，实现原子问的检索，一般用于检索与原子问相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "atomic_query_extractor",
                "llm": llm_config,
                "prompt": {"type": "atomic_query_extract"},
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "atomic_query_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "score_threshold": 0.7,
                "llm_client": llm_config,
                "query_rewrite_prompt": {"type": "atomic_query_rewrite_prompt"},
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "graph_api": {
                    "type": "openspg_graph_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
            {
                "type": "vector_chunk_retriever",
                "score_threshold": 0.7,
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
            {
                "type": "text_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]


@KAGIndexManager.register("chunk_index")
class ChunkIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于文本块的索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器将文档直接分割成文本块（Chunk），并为这些文本块创建向量和文本索引。这是一种直接而高效的索引方式（Naive RAG），适用于对整个文档进行语义或关键字检索，快速定位包含相关信息的文本片段。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector        
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：
        
        1、抽取模型消耗：7B 0 tokens
        2、耗时：1.5 秒
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        return """
        **适用场景**: 适用于通用、开放式的文档问答，当问题没有特定结构，需要在大量非结构化文本中寻找答案时。

        **检索流程**:
        1. `rewrite(sub_query)`: 对用户问题进行重写。
        2. `recall_chunks(...)`: 直接在所有文本块中进行向量或关键词搜索，召回最相关的文本块。

        **代码示例**:
        `chunks = recall_chunks(rewrite(sub_query))`
        """

    @property
    def retrieval_method(self) -> str:
        return "通过构建chunk 索引，实现chunk 的检索，一般用于检索与chunk 相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "naive_rag_extractor",
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "vector_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
            {
                "type": "text_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]


@KAGIndexManager.register("table_index")
class TableIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于表格的索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器专门用于识别和抽取文档中的表格数据，并为其内容、上下文（前后文本）创建索引。它能够精确地检索表格，并利用表格与周围文本的关联关系来召回相关的文本块，非常适合处理包含大量结构化表格数据的文档。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector
Table(表格): IndexType
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
        
        1、抽取模型消耗：7B 0 tokens
        2、耗时：1.5 秒
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        return """
        **适用场景**: 当问题涉及到查询表格中的数据时，例如"XX产品的价格是多少？"或者需要引用表格内容进行回答的场景。

        **检索流程**:
        1. `rewrite(sub_query)`: 对用户问题进行重写。
        2. `recall_table(...)`: 根据问题内容，搜索并召回最相关的表格。
        3. `get_table_associate_chunks(...)`: 找到与召回表格相关联的文本块，提供更丰富的上下文。

        **代码示例**:
        `chunks = get_table_associate_chunks(recall_table(rewrite(sub_query)))`
        """

    @property
    def retrieval_method(self) -> str:
        return "通过构建表格索引，实现表格的检索，一般用于检索与表格相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "table_extractor",
                "llm": llm_config,
                "table_context_prompt": {"type": "table_context"},
                "table_row_col_summary_prompt": {"type": "table_row_col_summary"},
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "table_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "graph_api": {
                    "type": "openspg_graph_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]


@KAGIndexManager.register("summary_index")
class SummaryIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于摘要的索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器利用大语言模型对文本块（Chunk）生成多层次的摘要（Summary），并基于这些摘要构建索引。通过检索摘要，可以快速理解大段文本的核心内容，并利用摘要与原始文本块的关联来召回详细信息，适用于需要信息概览和层层深入的检索场景。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector
Summary(文本摘要): IndexType
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
        return """
        **适用场景**: 适用于需要对长文档进行归纳总结，或者需要从宏观到微观层层钻取信息的场景。

        **检索流程**:
        1. `rewrite(sub_query)`: 对用户问题进行重写。
        2. `recall_summary(...)`: 根据问题搜索并召回最相关的摘要。
        3. `get_summary_associate_chunks(...)`: 通过召回的摘要，找到其对应的原始文本块，提供详细信息。

        **代码示例**:
        `chunks = get_summary_associate_chunks(recall_summary(rewrite(sub_query)))`
        """

    @property
    def retrieval_method(self) -> str:
        return "通过大模型总结的摘要，实现摘要的检索，一般用于检索与摘要相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "summary_extractor",
                "llm_module": llm_config,
                "chunk_summary_prompt": {"type": "default_chunk_summary"},
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "summary_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "graph_api": {
                    "type": "openspg_graph_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "score_threshold": 0.8,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]


@KAGIndexManager.register("outline_index")
class OutlineIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于大纲的索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器通过解析文档的结构（如标题层级）来构建大纲（Outline）索引。这种索引保留了文档的层次结构，允许用户通过检索章节标题来快速定位到文档的特定部分，并召回与该大纲节点相关的文本块。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector
Outline(标题大纲): IndexType
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
        
        1、抽取模型消耗：7B 0 tokens
        2、耗时：9.4 秒
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        return """
        **适用场景**: 适用于结构化文档的问答，特别是当问题与文档的特定章节或标题相关时。

        **检索流程**:
        1. `rewrite(sub_query)`: 对用户问题进行重写。
        2. `recall_outline(...)`: 根据问题搜索召回最相关的大纲标题，并可沿着大纲层级扩展。
        3. `get_outline_associate_chunks(...)`: 根据召回的大纲，找到其对应的文本块。

        **代码示例**:
        `chunks = get_outline_associate_chunks(recall_outline(rewrite(sub_query)))`
        """

    @property
    def retrieval_method(self) -> str:
        return "通过构建时文本的大纲，实现大纲的检索，一般用于检索与大纲相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "outline_extractor",
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "outline_chunk_retriever",
                "vectorize_model": vectorize_model_config,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "graph_api": {
                    "type": "openspg_graph_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "top_k": 10,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]


@KAGIndexManager.register("kag_hybrid_index")
class KAGHybridIndexManager(KAGIndexManager):
    @property
    def name(self):
        return "基于文本块和图谱的混合索引管理器"

    @property
    def description(self) -> str:
        return "该索引管理器是一种混合方法，它结合了知识图谱（KG）和文本块（Chunk）的优点。它首先从文本中抽取实体和关系构建图谱，然后将文本块与图谱节点关联起来。在检索时，它同时利用图谱的结构化查询能力（CS/FR Retriever）和文本的向量检索能力，实现更精准、更具推理能力的检索，特别适合复杂的问答任务。"

    @property
    def schema(self) -> str:
        return """
Chunk(文本块): IndexType
     properties:
        content(内容): Text
          index: TextAndVector  

KnowledgeUnit(知识点): IndexType
     properties:
        structedContent(结构化文本): Text
          index: TextAndVector
        ontology(本体): Text
        desc(描述): Text
            index: TextAndVector
        relatedQuery(关联问): AtomicQuery
        extendedKnowledge(关联外扩知识点):Text
        content(内容): Text
            index: TextAndVector
        knowledgeType(知识类型): Text

AtomicQuery(原子问): IndexType
  properties:
    title(标题): Text
      index: TextAndVector
  relations:
    sourceChunk(关联文本块): Chunk
    similar(相似问题): AtomicQuery
    relatedTo(相关): KnowledgeUnit      
        """

    @property
    def index_cost(self) -> str:
        msg = """
        索引构建的成本：

        1、抽取模型消耗：7B 4634332 tokens
        2、耗时：1425 秒
        3、文件字数：10万字
        """
        return msg

    @property
    def applicable_scenarios(self) -> str:
        return """
        **适用场景**: 适用于需要深度推理和关联分析的复杂问题。它能够理解问题的结构，并在知识图谱和文本块之间进行联合查询，应对需要跨领域知识或多跳推理的场景。

        **检索流程（多路并行）**:
        - **路径1 (FR)**: `kg_fr_retriever(query)` -> 自由文本检索，召回相关文本块。
        - **路径2 (CS)**: `kg_cs_retriever(logic_form)` -> 基于问题的逻辑结构，在图谱中进行精确检索。
        - **路径3 (RC)**: `vector_chunk_retriever(query)` -> 纯向量检索，作为补充召回。
        
        最终将多路结果融合，提供最全面的答案依据。
        """

    @property
    def retrieval_method(self) -> str:
        return "通过构建chunk 与 图谱的关联，实现图谱、chunk 的检索，一般用于检索与图谱相关的chunk"

    @classmethod
    def build_extractor_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "knowledge_unit_extractor",
                "ner_prompt": "knowledge_unit_ner",
                "triple_prompt": "knowledge_unit_triple",
                "kn_prompt": "knowledge_unit",
                "llm": llm_config,
                "kag_qa_task_config_key": kb_task_project_id,
            }
        ]

    @classmethod
    def build_retriever_config(
        cls, llm_config: Dict, vectorize_model_config: Dict, **kwargs
    ):
        kb_task_project_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        return [
            {
                "type": "kg_cs_open_spg",
                "path_select": {
                    "type": "exact_one_hop_select",
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "graph_api": {
                        "type": "openspg_graph_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.9,
                    "exclude_types": ["Chunk"],
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "graph_api": {
                        "type": "openspg_graph_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "std_schema": {
                    "type": "default_std_schema",
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "llm": llm_config,
                "kag_qa_task_config_key": kb_task_project_id,
            },
            {
                "type": "kg_fr_knowledge_unit",
                "top_k": 20,
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "graph_api": {
                    "type": "openspg_graph_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "path_select": {
                    "type": "fuzzy_one_hop_select",
                    "llm_client": llm_config,
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "graph_api": {
                        "type": "openspg_graph_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "ppr_chunk_retriever_tool": {
                    "type": "ppr_chunk_retriever",
                    "llm_client": llm_config,
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "graph_api": {
                        "type": "openspg_graph_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                    "ner": {
                        "type": "ner",
                        "kag_qa_task_config_key": kb_task_project_id,
                        "ner_prompt": {
                            "type": "default_question_ner",
                            "kag_qa_task_config_key": kb_task_project_id,
                        },
                        "std_prompt": {"type": "default_std"},
                        "llm_module": llm_config,
                    },
                },
                "entity_linking": {
                    "type": "entity_linking",
                    "recognition_threshold": 0.8,
                    "exclude_types": ["Chunk"],
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "graph_api": {
                        "type": "openspg_graph_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "std_schema": {
                    "type": "default_std_schema",
                    "vectorize_model": vectorize_model_config,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "llm": llm_config,
                "kag_qa_task_config_key": kb_task_project_id,
            },
            {
                "type": "rc_open_spg",
                "search_api": {
                    "type": "openspg_search_api",
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "vector_chunk_retriever": {
                    "type": "vector_chunk_retriever",
                    "vectorize_model": vectorize_model_config,
                    "score_threshold": 0.65,
                    "search_api": {
                        "type": "openspg_search_api",
                        "kag_qa_task_config_key": kb_task_project_id,
                    },
                    "kag_qa_task_config_key": kb_task_project_id,
                },
                "vectorize_model": vectorize_model_config,
                "top_k": 20,
                "kag_qa_task_config_key": kb_task_project_id,
            },
        ]
