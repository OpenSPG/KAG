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
from string import Template
from typing import List
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF


@Registrable.register("prompt")
class PromptABC(Registrable, ABC):
    """
    Provides a template for generating and parsing prompts related to specific business scenes.

    Subclasses must implement the template strings for specific languages (English or Chinese)
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
        if not language:
            language = KAG_PROJECT_CONF.language
        self.language = language

        if not hasattr(self, f"template_{self.language}"):
            raise ValueError(f"language {self.language} not supported yet.")

        self.template = getattr(self, f"template_{self.language}")

        self.template_variables_value = {}

    @property
    def project_id(self):
        return KAG_PROJECT_CONF.project_id

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
        new_template_str = template_string.replace("$", "$$")
        for var in self.template_variables:
            new_template_str = new_template_str.replace(f"$${var}", f"${var}")
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
        template_string = self.process_template_string_to_avoid_dollar_problem(
            self.template
        )
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
