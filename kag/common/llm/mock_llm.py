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

import time
import json
from kag.interface import LLMClient


@LLMClient.register("mock")
class MockLLMClient(LLMClient):
    """
    MockLLMClient is a mock implementation of the LLMClient class, used for testing purposes.

    This class provides a method to simulate the behavior of a language model client by matching input prompts.
    """

    def __init__(
        self,
        max_rate: float = 1000,
        time_period: float = 1,
        **kwargs,
    ):
        """
        Initializes the MockLLMClient instance.
        """
        name = kwargs.get("name", None)
        if not name:
            name = "mock"

        super().__init__(name, max_rate, time_period)

    def match_input(self, prompt):
        """
        Simulates the behavior of a language model call by matching the input prompt.

        Args:
            prompt: The input prompt to be matched.
        """
        time.sleep(0.3)  # mimic llm call
        if "You're a very effective entity extraction system" in prompt:
            return [
                {
                    "entity": "The Rezort",
                    "type": "Movie",
                    "category": "Works",
                    "description": "A 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger.",
                },
                {
                    "entity": "2015",
                    "type": "Year",
                    "category": "Date",
                    "description": "The year the movie 'The Rezort' was released.",
                },
            ]
        if "please attempt to provide the official names of" in prompt:
            return [
                {
                    "entity": "The Rezort",
                    "type": "Movie",
                    "category": "Works",
                    "description": "A 2015 British zombie horror film directed by Steve Barker and written by Paul Gerstenberger.",
                },
                {
                    "entity": "2015",
                    "type": "Year",
                    "category": "Date",
                    "description": "The year the movie 'The Rezort' was released.",
                },
            ]
        if (
            "You are an expert specializing in carrying out open information extraction"
            in prompt
        ):
            return [
                ["The Rezort", "is", "zombie horror film"],
                ["The Rezort", "publish at", "2015"],
            ]
        return "I am an intelligent assistant"

    def __call__(self, prompt, **kwargs):
        return json.dumps(self.match_input(prompt))

    def call_with_json_parse(self, prompt, **kwargs):
        return self.match_input(prompt)

    async def acall(self, prompt, **kwargs):
        return json.dumps(self.match_input(prompt))

    async def acall_with_json_parse(self, prompt, **kwargs):
        return self.match_input(prompt)
