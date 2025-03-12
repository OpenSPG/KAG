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
from kag.interface import GeneratorABC


@GeneratorABC.register("mock_generator")
class MockGenerator(GeneratorABC):
    def invoke(self, query, context):
        results = []
        for task in context.gen_task(False):
            results.append(
                {
                    "action": {"name": task.executor, "arguments": task.arguments},
                    "result": task.result,
                }
            )
        return f"Query: {query}\nOutput: {results}"
