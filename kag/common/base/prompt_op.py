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

import importlib
import inspect
import os
import sys
from abc import ABC
from string import Template
from typing import List


BUILDER_PROMPT_PATH = "kag.builder.prompt"
SOLVER_PROMPT_PATH = "kag.solver.prompt"


class PromptOp(ABC):
    """
    Provides a template for generating and parsing prompts related to specific business scenes.

    Subclasses must implement the template strings for specific languages (English or Chinese)
    and override the `template_variables` and `parse_response` methods.
    """

    """English template string"""
    template_en: str = ""
    """Chinese template string"""
    template_zh: str = ""

    def __init__(self, language: str, **kwargs):
        """
        Initializes the PromptOp instance with the selected language.

        Args:
            language (str): The language for the prompt, should be either "en" or "zh".

        Raises:
            AssertionError: If the provided language is not supported.
        """

        assert language in ["en", "zh"], f"language[{language}] is not supported."
        self.template = self.template_en if language == "en" else self.template_zh
        self.language = language
        self.template_variables_value = {}
        if "project_id" in kwargs:
            self.project_id = kwargs["project_id"]

    @property
    def template_variables(self) -> List[str]:
        """
        Gets the list of template variables.

        Must be implemented by subclasses.

        Returns:
        - List[str]: A list of template variable names.

        Raises:
        - NotImplementedError: If the subclass does not implement this method.
        """

        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `template_variables` method."
        )

    def process_template_string_to_avoid_dollar_problem(self, template_string):
        new_template_str = template_string.replace('$', '$$')
        for var in self.template_variables:
            new_template_str = new_template_str.replace(f'$${var}', f'${var}')
        return new_template_str

    def build_prompt(self, variables) -> str:
        """
        Build a prompt based on the template and provided variables.

        This method replaces placeholders in the template with actual variable values.
        If a variable is not provided, it defaults to an empty string.

        Parameters:
        - variables: A dictionary containing variable names and their corresponding values.

        Returns:
        - A string or list of strings, depending on the template content.
        """

        self.template_variables_value = variables
        template_string = self.process_template_string_to_avoid_dollar_problem(self.template)
        template = Template(template_string)
        return template.substitute(**variables)

    def parse_response(self, response: str, **kwargs):
        """
        Parses the response string.

        Must be implemented by subclasses.

        Parameters:
        - response (str): The response string to be parsed.

        Raises:
        - NotImplementedError: If the subclass does not implement this method.
        """

        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `parse_response` method."
        )

    @classmethod
    def load(cls, biz_scene: str, type: str):
        """
        Dynamically loads the corresponding PromptOp subclass object based on the business scene and type.

        Parameters:
        - biz_scene (str): The name of the business scene.
        - type (str): The type of prompt.

        Returns:
        - subclass of PromptOp: The loaded PromptOp subclass object.

        Raises:
        - ImportError: If the specified module or class does not exist.
        """
        dir_paths = [
            os.path.join(os.getenv("KAG_PROJECT_ROOT_PATH", ""), "builder", "prompt"),
            os.path.join(os.getenv("KAG_PROJECT_ROOT_PATH", ""), "solver", "prompt"),
        ]
        module_paths = [
            '.'.join([BUILDER_PROMPT_PATH, biz_scene, type]),
            '.'.join([SOLVER_PROMPT_PATH, biz_scene, type]),
            '.'.join([BUILDER_PROMPT_PATH, 'default', type]),
            '.'.join([SOLVER_PROMPT_PATH, 'default', type]),
        ]

        def find_class_from_dir(dir, type):
            sys.path.append(dir)

            for root, dirs, files in os.walk(dir):
                for file in files:
                    if file.endswith(".py") and file.startswith(f"{type}."):
                        module_name = file[:-3]
                        try:
                            module = importlib.import_module(module_name)
                        except ImportError:
                            continue
                        cls_found = find_class_from_module(module)
                        if cls_found:
                            return cls_found
            return None

        def find_class_from_module(module):
            classes = inspect.getmembers(module, inspect.isclass)
            for class_name, class_obj in classes:
                import kag
                if issubclass(class_obj, kag.common.base.prompt_op.PromptOp) and inspect.getmodule(class_obj) == module:
                    return class_obj
            return None

        for dir_path in dir_paths:
            try:
                cls_found = find_class_from_dir(dir_path, type)
                if cls_found:
                    return cls_found
            except ImportError:
                continue

        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)
                cls_found = find_class_from_module(module)
                if cls_found:
                    return cls_found
            except ModuleNotFoundError:
                continue

        raise ValueError(f'Not support prompt with biz_scene[{biz_scene}] and type[{type}]')
