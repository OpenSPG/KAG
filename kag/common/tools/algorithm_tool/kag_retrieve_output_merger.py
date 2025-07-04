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
import math
from typing import List
from kag.interface import (
    Task,
    RetrieverOutputMerger,
    RetrieverOutput,
    ChunkData,
    KgGraph,
)


@RetrieverOutputMerger.register("kag_merger")
class KAGRetrieverOutputMerger(RetrieverOutputMerger):
    """A custom merger implementation for combining retrieved chunks from multiple retrievers.

    Attributes:
        name (str): Identifier for the merger instance.
        merge_method (str): Method used for merging results ("rrf" or "weightd").
        score_normalizer (callable): Normalization function based on merge_method.
    """

    def __init__(
        self,
        merge_method: str = "rrf",
        **kwargs,
    ):
        """Initializes the merger with specified normalization strategy.

        Args:
            merge_method: Method for score normalization ("rrf" for reciprocal rank fusion
                or "weightd" for min-max normalization). Defaults to "rrf".
            **kwargs: Additional keyword arguments for base class initialization.
        """
        super().__init__(**kwargs)
        self.merge_method = merge_method
        if self.merge_method.lower().strip() == "weightd":
            self.score_normalizer = self.min_max_normalize
        else:
            self.score_normalizer = self.rrf_normalize

    def min_max_normalize(self, chunks: List[ChunkData]):
        """Normalizes chunk scores using min-max scaling.

        Args:
            chunks: List of ChunkData objects to normalize.

        Returns:
            None: Modifies chunks in-place by updating their score attributes.
        """
        if len(chunks) == 0:
            return []
        scores = [x.score for x in chunks]
        max_score = max(scores)
        min_score = min(scores)
        for chunk in chunks:
            score = chunk.score
            if math.isclose(max_score, min_score, rel_tol=1e-9):
                score = 1
            else:
                score = (score - min_score) / (max_score - min_score)
            chunk.score = score

    def rrf_normalize(self, chunks: List[ChunkData]):
        """Normalizes scores using reciprocal rank fusion (RRF) method.

        Args:
            chunks: List of ChunkData objects to normalize.

        Returns:
            None: Modifies chunks in-place by updating their score attributes.
        """
        if len(chunks) == 0:
            return []
        for idx, chunk in enumerate(chunks):
            score = 1 / (idx + 1)
            chunk.score = score

    def chunk_merge(self, chunk_lists: List[List[ChunkData]], score_normalizer):
        """Merges multiple chunk lists into a unified ranked list.

        Args:
            chunk_lists: Multiple lists of ChunkData from different retrievers.
            score_normalizer: Normalization function to apply before merging.

        Returns:
            List[ChunkData]: Merged and sorted list of chunks with aggregated scores.
        """
        merged = {}
        chunk_map = {}
        for chunks in chunk_lists:
            score_normalizer(chunks)
            for chunk in chunks:
                chunk_id = chunk.chunk_id
                if chunk_id in merged:
                    merged[chunk_id] += chunk.score
                else:
                    merged[chunk_id] = chunk.score
                if chunk_id not in chunk_map:
                    chunk_map[chunk_id] = chunk
        sorted_chunk_ids = sorted(merged.items(), key=lambda x: -x[1])
        output = []
        for item in sorted_chunk_ids:
            chunk_id, score = item
            chunk = chunk_map[chunk_id]
            output.append(
                ChunkData(
                    content=chunk.content,
                    title=chunk.title,
                    chunk_id=chunk.chunk_id,
                    score=score,
                )
            )

        return output

    def invoke(
        self, task: Task, retrieve_outputs: List[RetrieverOutput], **kwargs
    ) -> RetrieverOutput:
        """Main entry point for merging retriever outputs.

        Args:
            task: Current processing task containing context information.
            retrieve_outputs: List of outputs from different retrievers.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            RetrieverOutput: Final merged output containing unified chunk list.
        """
        retrieved_chunks = kwargs.get("retrieved_chunks", None)
        chunk_lists = [x.chunks for x in retrieve_outputs]
        merged = self.chunk_merge(chunk_lists, self.score_normalizer)
        if retrieved_chunks is not None:
            chunk_texts = [x.content for x in merged]
            retrieved_chunks.extend(chunk_texts)
        graph = KgGraph()
        for x in retrieve_outputs:
            for g in x.graphs:
                graph.merge_kg_graph(g)
        return RetrieverOutput(
            retriever_method=self.name,
            chunks=merged,
            graphs=[graph],
        )

    def schema(self):
        return {"name": "kag_merger"}
