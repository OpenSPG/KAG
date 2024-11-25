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
from typing import Union, List, Dict

from kag.common.base.component import Component
from kag.common.base.runnable import Input, Output


class BuilderComponent(Component, ABC):
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


class SourceReader(BuilderComponent, ABC):
    """
    Abstract base class for all source reader component.
    """

    @property
    def upstream_types(self):
        return None

    @property
    def downstream_types(self):
        return Union[Extractor, Mapping]


class Splitter(BuilderComponent, ABC):
    """
    Abstract base class for all splitter component.
    """

    @property
    def upstream_types(self):
        return SourceReader

    @property
    def downstream_types(self):
        return Union[Extractor, Mapping]


class Extractor(BuilderComponent, ABC):
    """
    Abstract base class for all extractor component.
    """

    @property
    def upstream_types(self):
        return Union[SourceReader, Extractor]

    @property
    def downstream_types(self):
        return Union[Extractor, Mapping]


class Aligner(BuilderComponent, ABC):
    """
    Abstract base class for all aligner component.
    """

    @property
    def upstream_types(self):
        return Union[SourceReader, Extractor]

    @property
    def downstream_types(self):
        return Union[Extractor, Mapping]


class Mapping(BuilderComponent, ABC):
    """
    Abstract base class for all mapping component.
    """

    @property
    def upstream_types(self):
        return Union[SourceReader, Extractor]

    @property
    def downstream_types(self):
        return Union[SinkWriter]


class PostProcessor(BuilderComponent, ABC):
    """
    Abstract base class for all post processor component.
    """

    @property
    def upstream_types(self):
        return Extractor

    @property
    def downstream_types(self):
        return SinkWriter


class SinkWriter(BuilderComponent, ABC):
    """
    Abstract base class for all sink writer component.
    """

    @property
    def upstream_types(self):
        return Union[Mapping]

    @property
    def downstream_types(self):
        return None
