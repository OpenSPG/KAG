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
from kag.interface import IndexABC


@IndexABC.register("chunk_index")
class ChunkIndex(IndexABC):
    @property
    def description(self) -> str:
        return "Chunk with optional text/vector index"

    @property
    def schema(self) -> List[str]:
        return ["Chunk"]

    @property
    def cost(self) -> str:
        return "very low"


@IndexABC.register("summary_index")
class SummaryIndex(IndexABC):
    @property
    def description(self) -> str:
        return "Chunk summary with optional text/vector index"

    @property
    def schema(self) -> List[str]:
        return ["Summary"]

    @property
    def cost(self) -> str:
        return "low"


@IndexABC.register("event_index")
class EventIndex(IndexABC):
    @property
    def description(self) -> str:
        return "Chunk event with optional text/vector index"

    @property
    def schema(self) -> List[str]:
        return ["Event"]

    @property
    def cost(self) -> str:
        return "low"


@IndexABC.register("atomic_query_index")
class AtomicQueryIndex(IndexABC):
    @property
    def description(self) -> str:
        return "Atomic query index with optional text/vector index"

    @property
    def schema(self) -> str:
        return ["AtomicQuery"]

    @property
    def cost(self) -> str:
        return "low"


@IndexABC.register("outline_index")
class OutlineIndex(IndexABC):
    @property
    def description(self) -> str:
        return "Atomic query index with optional text/vector index"

    @property
    def schema(self) -> str:
        return ["Outline"]

    @property
    def cost(self) -> str:
        return "low"


@IndexABC.register("graph")
@IndexABC.register("spo_graph_index")
class GraphIndex(IndexABC):
    @property
    def description(self) -> str:
        return ""

    @property
    def schema(self) -> List[str]:
        return ["Graph"]

    @property
    def cost(self) -> str:
        return ""
