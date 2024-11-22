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
from typing import List, Dict

from knext.common.base.component import Component
from knext.common.base.runnable import Input, Output
from kag.common.registry import Registrable


@Registrable.register("builder")
class BuilderComponent(Component, Registrable):
    """
    Abstract base class for all builder component.
    """

    @property
    def type(self):
        """
        Get the type label of the object.

        Returns:
            str: The type label of the object, fixed as "BUILDER".
        """
        return "BUILDER"

    def batch(self, inputs: List[Input], **kwargs) -> List[Output]:
        results = []
        for input in inputs:
            results.extend(self.invoke(input, **kwargs))
        return results

    def _handle(self, input: Dict) -> List[Dict]:
        _input = self.input_types.from_dict(input) if isinstance(input, dict) else input
        _output = self.invoke(_input)
        return [_o.to_dict() for _o in _output if _o]
