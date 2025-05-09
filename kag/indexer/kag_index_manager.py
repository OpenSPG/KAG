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

from typing import List

from knext.schema.client import SchemaClient
from kag.interface.builder.extractor_abc import ExtractorABC
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF
from kag.solver.executor.retriever.local_knowledge_base.kag_retriever.kag_hybrid_executor import (
    KagHybridExecutor as Retriever,
)


class KAGIndexManager(Registrable):
    def __init__(
        self,
        index_builder: List[ExtractorABC],
        retriever: Retriever,
    ):
        self.index_builder = index_builder
        self.retriever = retriever

        self.indices = {}
        index_names = []
        for item in self.index_builder:
            index_names.extend(item.output_indices)

        extractor_register_dict = Registrable._registry[ExtractorABC]
        for index_name in index_names:
            cls, _ = extractor_register_dict[index_name]
            self.indices[index_name] = cls()

        self.project_schema = SchemaClient(
            host_addr=KAG_PROJECT_CONF.host_addr, project_id=KAG_PROJECT_CONF.project_id
        ).load()

    @property
    def description(self) -> str:
        index_desc = {k: v.description for k, v in self.indices.items()}
        return f"The indexer contains following indices:\n{index_desc}"

    @property
    def schema(self) -> str:
        schema_keys = []
        for item in self.indices.values():
            schema_keys.extend(item.schema)

        for schema_key in schema_keys:
            if schema_key == "Graph":
                continue
            if schema_key not in self.project_schema:
                raise ValueError(
                    f"index {schema_key} not in project indxe schema, please check your index config."
                )
        index_schema = [x.schema for x in self.indices.values()]
        return "\n".join(index_schema)

    @property
    def cost(self) -> str:
        index_costs = {k: v.cost for k, v in self.indices.items()}
        return f"The cost of each index are as follow:\n{index_costs}"
