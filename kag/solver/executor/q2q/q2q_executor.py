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
from kag.interface import ExecutorABC, Context, Task

@ExecutorABC.register("q2q_executor")
class Q2qExecutor(ExecutorABC):

    @property
    def category(self):
        return "Q2Q"

    def invoke(self, query: str, task: Task, context: Context, **kwargs):
        """Retrieval of user query from a knowledge base.

        Args:
            query: User query triggering the retrieval
            task: Task instance containing execution parameters
            context: Pipeline execution context with dependency tracking
            **kwargs: Additional execution parameters

        Returns:
            List of strings containing mock financial data entries
        """
        pass

    def schema(self):
        return {
            "name": "Q2Q",
            "description": "Performs query-to-query operations and is solely used to indicate that the task has been completed.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
