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
from typing import Type, List


class RESTable(ABC):
    """
    Abstract base class that can be serialized as REST model and submit to the SPG server.
    """

    @property
    def upstream_types(self) -> List[Type["RESTable"]]:
        """The types of upstream RESTable objects that the current RESTable object can support.

        Returns: RESTable type list.

        """
        return []

    @property
    def downstream_types(self) -> List[Type["RESTable"]]:
        """The types of downstream RESTable objects that the current RESTable object can support.

        Returns: RESTable type list.

        """
        return []

    def to_rest(self):
        """Convert a RESTable object to REST model that can be serialized.

        Returns: REST model.

        """
        raise NotImplementedError(
            f"`to_rest` is not currently supported for {self.__class__.__name__}."
        )

    @classmethod
    def from_rest(cls, rest_model):
        """Convert a REST model to RESTable object.

        Args:
            rest_model: REST model that needs to be converted to a RESTable object.

        Returns: Object inherits from RESTable.

        """
        raise NotImplementedError(
            f"`from_rest` is not currently supported for {cls.__name__}."
        )
