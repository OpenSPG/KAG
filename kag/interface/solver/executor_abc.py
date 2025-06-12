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
import inspect
from abc import ABC, abstractmethod

from docstring_parser import parse
from typing import Dict, Any, List

from kag.common.registry import Registrable
from kag.interface import Context


class ExecutorResponse(Registrable, ABC):
    """Abstract base class for recording executor responses.

    Subclasses must implement the to_string method to provide a string
    representation of the execution result.
    """

    def __init__(self):
        """Initializes the executor response instance."""
        pass

    def __str__(self):
        return self.to_string()

    __repr__ = __str__

    @abstractmethod
    def to_string(self) -> str:
        """Generates a string representation of the executor response.

        Returns:
            String representation of the execution result.

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError("to_string not implemented yet.")


class ExecutorABC(Registrable):
    """Abstract base class for task executors that perform actual computation."""

    def __init__(self, **kwargs):
        """Initializes the executor instance."""
        super().__init__(**kwargs)

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return ExecutorResponse

    @property
    def category(self):
        """Specifies the executor category used for generating function call schemas.

        Returns:
            str: Identifier representing the executor's category ("Empty" by default).
        """
        return "Empty"

    def invoke(self, query, task, context: Context, **kwargs):
        """Synchronously executes the given task.

        Args:
            query: Original user query/input that initiated the execution.
            task: Task instance to be executed.
            context: Execution context containing task dependencies.
            **kwargs: Additional execution parameters.

        Returns:
            ExecutorResponse containing the execution results.

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, task, context: Context, **kwargs):
        """Asynchronously executes the given task (default implementation runs sync invoke in thread).

        Args:
            query: Original user query/input that initiated the execution.
            task: Task instance to be executed.
            context: Execution context containing task dependencies.
            **kwargs: Additional execution parameters.

        Returns:
            ExecutorResponse containing the execution results.
        """
        return await asyncio.to_thread(
            lambda: self.invoke(query, task, context, **kwargs)
        )

    def parse_function_schema(self, func) -> Dict[str, Any]:
        """
        Parses a function's Google Style Docstring and parameters into a schema dictionary.

        Args:
            func (callable): The function to parse.

        Returns:
            dict: A dictionary containing the function's schema with name, description, and parameters.
        """
        docstring = parse(func.__doc__ or "")

        description = docstring.short_description or ""
        if docstring.long_description:
            description += "\n" + docstring.long_description

        signature = inspect.signature(func)
        parameters = {}
        for param in signature.parameters.values():
            param_info = {
                "type": "any",
                "description": "",
                "optional": param.default is not inspect.Parameter.empty,
            }
            parameters[param.name] = param_info

        for doc_param in docstring.params:
            if doc_param.arg_name in parameters:
                param = parameters[doc_param.arg_name]
                param["type"] = doc_param.type_name or param.get("type", "any")
                param["description"] = doc_param.description or param.get(
                    "description", ""
                )

        skiped_param_names = ["kwargs", "task", "context"]
        filtered_parameters = {}
        for k, v in parameters.items():
            if k not in skiped_param_names:
                filtered_parameters[k] = v

        return {
            "name": self.category,
            "description": description.strip(),
            "parameters": filtered_parameters,
        }

    def schema(self, func_name: str = None):
        """Generates interface schema for the executor.

        Args:
            func_name: Optional name of method to inspect. Defaults to:
                1. ainvoke if exists
                2. invoke if exists
                3. __call__ if exists

        Returns:
            Interface schema dictionary generated by parse_function_schema()

        Raises:
            ValueError: If no valid executor method is found
        """

        if not func_name:
            if hasattr(self, "ainvoke"):
                func = self.ainvoke
            elif hasattr(self, "invoke"):
                func = self.invoke
            elif hasattr(self, "__call__"):
                func = self.__call__
            else:
                raise ValueError("no func name found")
        else:
            func = getattr(self, func_name)
        return self.parse_function_schema(func)

    def report_content(self, reporter, segment, tag_id, content, status, **kwargs):
        if reporter:
            reporter.add_report_line(segment, tag_id, content, status, **kwargs)


class RetrieverABC(ExecutorABC):
    @staticmethod
    def input_indices() -> List[str]:
        return []
