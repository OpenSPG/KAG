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
from typing import List, Union, Any
from kag.builder.model.sub_graph import Node, SubGraph
from kag.common.registry import Registrable
from kag.interface.builder.base import BuilderComponent
from knext.common.base.runnable import Input, Output


class MatchConfig(Registrable):
    def __init__(self, k: int = 1, labels: List[str] = None, threshold: float = 0.9):
        self.k = k
        self.labels = labels
        self.threshold = threshold


MatchConfig.register("base", as_default=True)(MatchConfig)


class ExternalGraphLoaderABC(BuilderComponent):
    def __init__(self, match_config: MatchConfig):
        self.match_config = match_config

    def dump(self) -> List[SubGraph]:
        raise NotImplementedError("dump not implemented yet.")

    def ner(self, content: str) -> List[Node]:
        raise NotImplementedError("ner not implemented yet.")

    def get_allowed_labels(self, labels: List[str] = None) -> List[str]:
        raise NotImplementedError("get_allowed_labels not implemented yet.")

    def match_entity(
        self,
        query: Union[str, List[float], np.ndarray],
    ):
        pass

    @property
    def input_types(self):
        return Any

    @property
    def output_types(self):
        return SubGraph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        return self.dump()
