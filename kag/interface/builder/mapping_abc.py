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

from abc import ABC
from typing import Dict

from kag.interface.builder.base import BuilderComponent
from kag.builder.model.sub_graph import SubGraph


class MappingABC(BuilderComponent, ABC):
    """
    Abstract base class for mapping structured dictionaries to a list of SubGraphs, which can be written into a Knowledge Graph (KG) storage.

    This class defines the interface for mapping operations and provides properties to define the input and output types.
    """

    @property
    def input_types(self):
        return Dict

    @property
    def output_types(self):
        return SubGraph

    @property
    def inherit_input_key(self):
        return True
