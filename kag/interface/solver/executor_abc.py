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
import asyncio
from abc import ABC, abstractmethod
from kag.common.registry import Registrable


class ExecutorResponse(Registrable, ABC):
    def __init__(self):
        pass

    @abstractmethod
    def to_string(self) -> str:
        raise NotImplementedError("to_string not implemented yet.")


class ExecutorABC(Registrable):
    def __init__(self):
        pass

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return ExecutorResponse

    def invoke(self, query, task, context, **kwargs):
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, task, context, **kwargs):
        return await asyncio.to_thread(lambda : self.invoke(query, task, context, **kwargs))

    def schema(self):
        return {
            "name": "Dummy",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User-provided query for retrieval.",
                    },
                },
            },
        }
