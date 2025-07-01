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
from typing import List
from kag.interface.builder.base import BuilderComponent
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph


class ExtractorABC(BuilderComponent):
    """
    Abstract base class for extracting sub graphs (which contain a list of nodes and a list of edges) from chunks.

    This class defines the interface for all extractor components that are responsible for processing input data
    and generating sub graphs as output. It inherits from `BuilderComponent` and `ABC` (Abstract Base Class).
    """

    @property
    def input_types(self):
        return Chunk

    @property
    def output_types(self):
        return SubGraph

    @property
    def inherit_input_key(self):
        return True

    @staticmethod
    def output_indices() -> List[str]:
        return []
