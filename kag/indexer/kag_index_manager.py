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

    def get_meta(self):
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "config": self._config,
        }

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
