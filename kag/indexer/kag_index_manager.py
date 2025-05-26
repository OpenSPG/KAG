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
from typing import List, Dict

from knext.schema.client import SchemaClient
from kag.interface import ExtractorABC, RetrieverABC, IndexABC
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF
from kag.solver.executor.retriever.kag_hybrid_retrieval_executor import (
    KAGHybridRetrievalExecutor as Retriever,
)


class KAGIndexManager(Registrable):
    def __init__(
        self,
        extractor: List[ExtractorABC],
        retriever: List[Retriever],
    ):
        self.extractor = extractor
        self.retriever = retriever

        self.indices = {}
        index_names = []
        for item in self.extractor:
            index_names.extend(item.output_indices())

        index_register_dict = Registrable._registry[IndexABC]
        for index_name in index_names:
            cls, _ = index_register_dict[index_name]
            self.indices[index_name] = cls()

        self.project_schema = SchemaClient(
            host_addr=KAG_PROJECT_CONF.host_addr, project_id=KAG_PROJECT_CONF.project_id
        ).load()

        self._config = None

    @property
    def name(self):
        return "KAG Index Manager"

    @property
    def description(self) -> str:
        index_desc = {k: v.description for k, v in self.indices.items()}
        return f"The indexer contains following indices:\n{index_desc}"

    @property
    def schema(self) -> str:
        schema_keys = []
        for item in self.indices.values():
            schema_keys.extend(item.schema)

        index_schema = []

        for schema_key in schema_keys:
            if schema_key == "Graph":
                continue
            if schema_key not in self.project_schema:
                raise ValueError(
                    f"index {schema_key} not in project indxe schema, please check your index config."
                )
            index_schema.append(str(self.project_schema[schema_key]))

        return "\n".join(index_schema)

    @property
    def cost(self) -> str:
        index_costs = {k: v.cost for k, v in self.indices.items()}
        return f"The cost of each index are as follow:\n{index_costs}"

    @property
    def as_default(self) -> bool:
        return False

    def get_meta(self):
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "config": self._config,
            "index_cost": self.index_cost,
            "retrieval_method": self.retrieval_method,
            "applicable_scenarios": self.applicable_scenarios,
            "as_default": self.as_default,
        }

    @property
    def applicable_scenarios(self) -> str:
        pass

    @property
    def index_cost(self) -> str:
        pass

    @property
    def retrieval_method(self) -> str:
        pass

    @classmethod
    def build_extractor_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return []

    @classmethod
    def build_retriever_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        return []

    @classmethod
    def init_from_llm_config(cls, llm_config: Dict, vectorize_model_config: Dict):
        extractor_config = cls.build_extractor_config(
            llm_config, vectorize_model_config
        )
        retriever_config = cls.build_retriever_config(
            llm_config, vectorize_model_config
        )
        extractors = [ExtractorABC.from_config(x) for x in extractor_config]
        retrievers = [RetrieverABC.from_config(x) for x in retriever_config]
        obj = cls(extractors, retrievers)
        obj._config = {"extractor": extractor_config, "retriever": retriever_config}
        return obj


@KAGIndexManager.register("atomic_query_index", constructor="init_from_llm_config")
class AtomicIndexManager(KAGIndexManager):
    """Index manager to manage the atomic query index build and document retrieval."""

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
        pass

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
