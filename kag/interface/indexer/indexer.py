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


from kag.common.registry import Registrable
from knext.schema.model.base import IndexTypeEnum
from kag.interface.builder.extractor_abc import ExtractorABC
from kag.interface.solver.executor_abc import ExecutorABC


class IndexABC(Registrable):
    """
    An abstract base class that defines the interface for indices.
    """

    def __init__(self, index_type: str = "TextAndVector"):
        if index_type.strip().lower() == IndexTypeEnum.Vector.value.lower():
            self._index_type = IndexTypeEnum.Vector
        elif index_type.strip().lower() == IndexTypeEnum.Text.value.lower():
            self._index_type = IndexTypeEnum.Text
        elif index_type.strip().lower() == IndexTypeEnum.TextAndVector.value.lower():
            self._index_type = IndexTypeEnum.TextAndVector
        else:
            avaliable_types = list(IndexTypeEnum.__members__.keys())
            raise ValueError(
                f"unsupported index type {index_type}, available index types: {avaliable_types}"
            )

    @property
    def description(self) -> str:
        return ""

    @property
    def schema(self) -> str:
        return ""

    @property
    def cost(self) -> str:
        return ""


class IndexerABC(Registrable):
    def __init__(
        self,
        extractor: ExtractorABC,
        retriever: ExecutorABC,
    ):
        self.extractor = extractor
        self.retriever = retriever

        self.indices = {}
        index_names = self.extractor.input_indices
        extractor_register_dict = Registrable._registry[ExtractorABC]
        for index_name in index_names:
            cls, _ = extractor_register_dict[index_name]
            self.indices[index_name] = cls()

    @property
    def description(self) -> str:
        index_desc = {k: v.description for k, v in self.indices.items()}
        return f"The indexer contains following indices:\n{index_desc}"

    @property
    def schema(self) -> str:
        index_schema = [x.schema for x in self.indices.values()]
        return "\n".join(index_schema)

    @property
    def cost(self) -> str:
        index_costs = {k: v.cost for k, v in self.indices.items()}
        return f"The cost of each index are as follow:\n{index_costs}"
