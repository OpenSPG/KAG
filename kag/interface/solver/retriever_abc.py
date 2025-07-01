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

from kag.common.conf import KAGConfigAccessor, KAGConstants
from kag.interface.common.model.retriever_data import KgGraph, ChunkData, DocData
from kag.interface.common.tools import ToolABC
from kag.interface.solver.planner_abc import Task


class RetrieverOutput:
    """Container class for storing retrieval outputs from different data sources.

    Attributes:
        graphs (List[KgGraph]): List of retrieved knowledge graph elements.
        chunks (List[ChunkData]): List of retrieved text/document chunks.
        docs (List[DocData]): List of retrieved complete documents.
        retriever_method (str): Name of the retrieval method that generated this output.
        summary (str): A concise summary of the retrieved content across all data sources.
    """

    def __init__(
        self,
        graphs: Optional[List[KgGraph]] = None,
        chunks: Optional[List[ChunkData]] = None,
        docs: Optional[List[DocData]] = None,
        retriever_method: str = "",
        summary: str = "",
        err_msg: str = "",
        task: Task = None,
    ):
        """Initializes retrieval output container with optional data components.

        Args:
            graphs: Optional list of knowledge graph elements. Defaults to empty list.
            chunks: Optional list of text/document chunks. Defaults to empty list.
            docs: Optional list of complete documents. Defaults to empty list.
            retriever_method:  Name of the retrieval method used to generate this output.
            summary: Optional summary string describing the overall retrieval results.
                     If provided, should encapsulate key insights from all result types.
        """
        self.graphs = graphs if graphs else []
        self.chunks = chunks if chunks else []
        self.docs = docs if docs else []
        self.retriever_method = retriever_method
        self.summary = summary
        self.err_msg = err_msg
        self.task = task

    def __str__(self):
        """Generates human-readable string representation of retrieval results.

        Returns:
            str: Formatted string showing graphs, chunks and docs in separate sections,
                 with each element represented by its dictionary form.
        """
        graphs = "\n".join([str(x.to_dict()) for x in self.graphs])
        chunks = "\n".join([str(x.to_dict()) for x in self.chunks])
        docs = "\n".join([str(x.to_dict()) for x in self.docs])
        return "\n".join(
            [
                f"Retrieved Graphs:\n{graphs}",
                f"Retrieved Chunks:\n{chunks}",
                f"Retrieved Docs:\n{docs}",
                f"Retriever Method: {self.retriever_method}",
                f"Summary:\n{self.summary}",
                f"Task:\n{self.task}",
            ]
        )

    def to_dict(self):
        """Converts retrieval results to structured dictionary format.

        Returns:
            Dictionary containing three keys:
            - 'graphs': List of dictionaries from KgGraph objects
            - 'chunks': List of dictionaries from ChunkData objects
            - 'docs': List of dictionaries from DocData objects
        """
        return {
            "graphs": [str(x.get_all_spo()) for x in self.graphs],
            "chunks": [x.to_dict() for x in self.chunks],
            "docs": [x.to_dict() for x in self.docs],
            "retriever_method": self.retriever_method,
            "summary": self.summary,
            "err_msg": self.err_msg,
            "task": str(self.task) if self.task else "",
        }


class RetrieverABC(ToolABC):
    """Abstract base class for retrieval tools that process tasks and return structured results.

    Attributes:
        top_k (int): Maximum number of items to retrieve. Defaults to 10.
    """

    def __init__(self, top_k: int = 10, **kwargs):
        """Initializes the retriever with configuration parameters.

        Args:
            top_k: Maximum number of retrieval results to return. Defaults to 10.
            **kwargs: Additional keyword arguments for base class initialization.
        """
        self.top_k = top_k
        super().__init__(**kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        self.kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = self.kag_config.global_config
        self.priority = kwargs.get("priority", 1)

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return RetrieverOutput

    @property
    def input_indices(self) -> List[str]:
        """Gets the list of required input identifiers.

        Returns:
            List[str]: Empty list indicating no specific input indices required.
        """
        return []

    def invoke(self, task: Task, **kwargs) -> RetrieverOutput:
        """Synchronously processes a task to retrieve relevant information.

        Args:
            task: Task object containing query/logical form for retrieval.
            **kwargs: Additional execution parameters.

        Returns:
            RetrieverOutput: Container with retrieved results.

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, task: Task, **kwargs) -> RetrieverOutput:
        """Asynchronously processes a task using synchronous implementation by default.

        Args:
            task: Task object containing query/logical form for retrieval.
            **kwargs: Additional execution parameters.

        Returns:
            RetrieverOutput: Container with retrieved results.

        Note:
            Default implementation wraps synchronous invoke() in a thread. Subclasses
            should override for proper asynchronous operation.
        """
        return await asyncio.to_thread(lambda: self.invoke(task, **kwargs))


class RetrieverOutputMerger(ToolABC):
    """Abstract base class for merging results from multiple retrieval outputs.

    Provides framework for implementing different merging strategies to combine
    results from various retrievers into a unified output.
    """

    def __init__(self, **kwargs):
        """Initializes the merger with base tool configuration.

        Args:
            **kwargs: Additional keyword arguments to pass to parent class initializer.
        """
        super().__init__(**kwargs)

    def invoke(
        self, task: Task, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        """Synchronously merges multiple retrieval results.

        Args:
            task: Contextual task object containing execution metadata
            retrieve_outputs: List of RetrieverOutput objects to merge
            **kwargs: Additional implementation-specific parameters

        Returns:
            RetrieverOutput: Consolidated retrieval results

        Raises:
            NotImplementedError: Must be implemented by concrete subclasses
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(
        self, task: Task, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        """Asynchronously merges multiple retrieval results.

        Args:
            task: Contextual task object containing execution metadata
            retrieve_outputs: List of RetrieverOutput objects to merge
            **kwargs: Additional implementation-specific parameters

        Returns:
            RetrieverOutput: Consolidated retrieval results

        Note:
            Default implementation delegates to synchronous invoke() in a thread.
            Subclasses should override for proper asynchronous merging.
        """
        return await asyncio.to_thread(
            lambda: self.invoke(task, retrieve_outputs, **kwargs)
        )
