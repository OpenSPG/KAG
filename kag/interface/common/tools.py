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

from kag.common.registry import Registrable


class ToolABC(Registrable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._name: str = kwargs.get("name", "")

    @property
    def name(self):
        return self._name if self._name else self.schema().get("name", "")

    def invoke(self, query, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs):
        raise NotImplementedError("ainvoke not implemented yet.")

    def schema(self):
        return {}
