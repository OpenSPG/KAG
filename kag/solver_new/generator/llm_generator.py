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
from kag.interface import GeneratorABC, LLMClient, PromptABC


@GeneratorABC.register("llm_generator")
class LLMGenerator(GeneratorABC):
    def __init__(self, llm_client: LLMClient, generated_prompt: PromptABC, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt

    def invoke(self, query, context):
        results = []
        for task in context.gen_task(False):
            results.append(
                str(task.result)
            )
        return self.llm_client.invoke({
            "query": query,
            "content": results
        }, self.generated_prompt)
