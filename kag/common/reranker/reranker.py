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


def rrf_score(length, r: int = 1):
    return np.array([1 / (r + i) for i in range(length)])


class Reranker:
    """
    This class provides a framework for a reranker,
    which is intended to re-rank the matches between queries and document passages.
    """

    def __init__(self):
        """
        Constructor for initializing the reranker class.
        Currently, there are no specific initialization parameters or operations.
        """
        pass

    def rerank(self, queries: List[str], passages: List[str]):
        """
        Function to re-rank queries and document passages,
        aiming to reorder the input query and passage pairs according to a certain strategy.

        Parameters:
        queries (List[str]): A list of strings containing queries that need to be re-ranked.
        passages (List[str]): A list of strings containing document passages that need to be re-ranked.

        The function is currently not implemented and raises an exception to indicate this.
        """
        raise NotImplementedError("rerank not implemented yet.")