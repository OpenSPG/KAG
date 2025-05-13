# -*- coding: utf-8 -*-
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

import asyncio
from typing import List, Optional
from kag.common.registry import Registrable
from kag.interface.common.data import KgGraph, ChunkData, DocData


class ToolABC(Registrable):
    def __init__(self):
        pass

    def invoke(self, query, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs):
        raise NotImplementedError("ainvoke not implemented yet.")

    def schema(self):
        return {}


class RetrieverOutput:
    def __init__(
        self,
        graphs: Optional[List[KgGraph]] = None,
        chunks: Optional[List[ChunkData]] = None,
        docs: Optional[List[DocData]] = None,
    ):
        self.graphs = graphs if graphs else []
        self.chunks = chunks if chunks else []
        self.docs = docs if docs else []

    def __str__(self):
        graphs = "\n".join([str(x.to_dict()) for x in self.graphs])
        chunks = "\n".join([str(x.to_dict()) for x in self.chunks])
        docs = "\n".join([str(x.to_dict()) for x in self.docs])
        return "\n".join(
            [
                f"Retrieved Graphs:\n{graphs}",
                f"Retrieved Chunks:\n{chunks}",
                f"Retrieved Docs:\n{docs}",
            ]
        )

    def to_dict(self):
        return {
            "graphs": [x.to_dict() for x in self.graphs],
            "chunks": [x.to_dict() for x in self.chunks],
            "docs": [x.to_dict() for x in self.docs],
        }


class RetrieverABC(ToolABC):
    def __init__(self, top_k: int = 10, **kwargs):
        """Initializes the executor instance."""
        self.top_k = top_k
        super().__init__(**kwargs)

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return RetrieverOutput

    @property
    def input_indices(self) -> List[str]:
        return []

    def invoke(self, query: str, **kwargs) -> RetrieverOutput:
        """Synchronously executes the given task.

        Args:
            query: User query/input that initiated the execution.
            **kwargs: Additional execution parameters.

        Returns:
            ExecutorResponse containing the execution results.

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query: str, **kwargs) -> RetrieverOutput:
        """Asynchronously executes the given task (default implementation runs sync invoke in thread).

        Args:
            query: User query/input that initiated the execution.

            **kwargs: Additional execution parameters.

        Returns:
            ExecutorResponse containing the execution results.
        """
        return await asyncio.to_thread(lambda: self.invoke(query, **kwargs))


class RetrieverOutputMerger(ToolABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def invoke(
        self, query: str, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(
        self, query: str, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        return await asyncio.to_thread(
            lambda: self.invoke(query, retrieve_outputs, **kwargs)
        )
