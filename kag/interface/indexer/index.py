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
from kag.common.registry import Registrable


class IndexABC(Registrable):
    """
    An abstract base class that defines the interface for indices.
    """

    @property
    def description(self) -> str:
        return ""

    @property
    def cost(self) -> str:
        return ""

    @property
    def schema(self) -> List[str]:
        return []
