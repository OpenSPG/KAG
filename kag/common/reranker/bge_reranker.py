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


import numpy as np
from typing import List

from .reranker import Reranker


def rrf_score(length, r: int = 1):
    """
    Calculates the RRF (Recursive Robust Function) scores.
    
    This function generates a score sequence of the given length, where each score is calculated based on the index according to the formula 1/(r+i).
    RRF is a method used in information retrieval and data analysis, and this function provides a way to generate weights based on document indices.
    
    Parameters:
    length: int, the length of the score sequence, i.e., the number of scores to generate.
    r: int, optional, default is 1. Controls the starting index of the scores. Increasing the value of r shifts the emphasis towards later scores.
    
    Returns:
    numpy.ndarray, an array containing the scores calculated according to the given formula.
    """
    return np.array([1 / (r + i) for i in range(length)])



class BGEReranker(Reranker):
    """
    BGEReranker class is a subclass of Reranker that reranks given queries and passages.
    
    This class uses the FlagReranker model from FlagEmbedding to score and reorder passages.
    
    Args:
        model_path (str): Path to the FlagReranker model.
        use_fp16 (bool): Whether to use half-precision floating-point numbers for computation. Default is True.
    """
    def __init__(self, model_path: str, use_fp16: bool = True):
        from FlagEmbedding import FlagReranker
        self.model_path = model_path
        self.model = FlagReranker(self.model_path, use_fp16=use_fp16)

    def rerank(self, queries: List[str], passages: List[str]):
        """
        Reranks given queries and passages.
        
        Args:
            queries (List[str]): List of queries.
            passages (List[str]): List of passages, where each passage is a string.
            
        Returns:
            new_passages (List[str]): List of passages after reranking.
        """
        # Calculate initial ranking scores for passages
        rank_scores = rrf_score(len(passages))
        passage_scores = np.zeros(len(passages)) + rank_scores
        
        # For each query, compute passage scores using the model and accumulate them
        for query in queries:
            scores = self.model.compute_score([[query, x] for x in passages])
            sorted_idx = np.argsort(-np.array(scores))
            for rank, passage_id in enumerate(sorted_idx):
                passage_scores[passage_id] += rank_scores[rank]
        
        # Perform final sorting of passages based on accumulated scores
        merged_sorted_idx = np.argsort(-passage_scores)
        
        new_passages = [passages[x] for x in merged_sorted_idx]
        return new_passages