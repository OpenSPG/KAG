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
import json
import copy
from abc import ABC
from string import Template
from typing import List
from kag.common.registry import Registrable
from kag.common.conf import KAGConstants, KAGConfigAccessor


@Registrable.register("prompt")
class PromptABC(Registrable, ABC):
    """
    Provides a template for generating and parsing prompts related to specific business scenes.

    Subclasses must implement the template for specific languages (Chinese or English)
    and override the `template_variables` and `parse_response` methods.
    """

    """English template string"""
    template_en: str = ""
    """Chinese template string"""
    template_zh: str = ""

    def __init__(self, language: str = "", **kwargs):
        """
        Initializes the prompt instance with the selected language.

        Args:
            language (str): The language for the prompt, Defaults to empty string, which will fallback to project.language config.

        Raises:
            AssertionError: If the provided language is not supported.
        """
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        if not language:
            language = self.kag_project_config.language
        self.language = language

        if not hasattr(self, f"template_{self.language}"):
            raise ValueError(f"language {self.language} not supported yet.")

        self.template = getattr(self, f"template_{self.language}")

        self.template_variables_value = {}
        self.example_input = kwargs.get("example_input", None)
        self.example_output = kwargs.get("example_output", None)
        if isinstance(self.example_output, str):
            try:
                self.example_output = json.loads(self.example_output)
            except:
                pass

    def is_json_format(self):
        return True

    @property
    def project_id(self):
        return self.kag_project_config.project_id

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
        """
        Processes the template string to avoid issues with dollar signs.

        Args:
            template_string (str): The template string to process.

        Returns:
        - str: The processed template string.
        """
        new_template_str = template_string.replace("$", "$$")
        for var in self.template_variables:
            new_template_str = new_template_str.replace(f"$${var}", f"${var}")
        return new_template_str

    def _build_dict_prompt(self, variables) -> str:
        """
        Builds a dictionary-based prompt with provided variables.

        Args:
            variables (dict): A dictionary of variables to include in the prompt.

        Returns:
        - str: The generated prompt as a JSON string.
        """
        tmpl = copy.deepcopy(self.template)
        tmpl.update(variables)
        if self.example_input and self.example_output:
            tmpl["example"] = {
                "input": self.example_input,
                "output": (
                    json.loads(self.example_output)
                    if isinstance(self.example_output, str)
                    else self.example_output
                ),
            }
        return json.dumps(tmpl, ensure_ascii=False)

    def _build_str_prompt(self, variables) -> str:
        """
        Builds a string-based prompt with provided variables.

        Args:
            variables (dict): A dictionary of variables to include in the prompt.

        Returns:
        - str: The generated prompt as a string.
        """
        template_string = self.process_template_string_to_avoid_dollar_problem(
            self.template
        )
        template = Template(template_string)
        prompt = template.substitute(**variables)
        if self.example_input and self.example_output:
            prompt = json.loads(prompt)
            prompt["example"] = {
                "input": self.example_input,
                "output": self.example_output,
            }
            prompt = json.dumps(prompt, ensure_ascii=False)
        return prompt

    def build_prompt(self, variables) -> str:
        """
        Builds a prompt based on the template and provided variables.

        This method replaces placeholders in the template with actual variable values.
        If a variable is not provided, it defaults to an empty string.

        Args:
            variables (dict): A dictionary containing variable names and their corresponding values.

        Returns:
        - str: The generated prompt, which may be a string or a JSON string depending on the template content.

        Raises:
        - ValueError: If the template format is unsupported.
        """
        self.template_variables_value = variables
        if isinstance(self.template, str):
            return self._build_str_prompt(variables)
        elif isinstance(self.template, dict):
            return self._build_dict_prompt(variables)
        raise ValueError(
            f"Unsupported template format, expect [str|dict], but got {type(self.template)}"
        )

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
