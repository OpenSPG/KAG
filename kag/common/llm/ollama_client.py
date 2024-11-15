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

import logging
from ollama import Client

from kag.common.llm.llm_client import LLMClient


# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@LLMClient.register("ollama")
class OllamaClient(LLMClient):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self.param = {}
        self.client = Client(host=self.base_url)

    def sync_request(self, prompt, image=None):
        # import pdb; pdb.set_trace()
        response = self.client.generate(model=self.model, prompt=prompt, stream=False)
        content = response["response"]
        content = content.replace("&rdquo;", "”").replace("&ldquo;", "“")
        content = content.replace("&middot;", "")

        return content

    def __call__(self, prompt, image=None):
        return self.sync_request(prompt, image)

    def call_with_json_parse(self, prompt):
        rsp = self.sync_request(prompt)
        _end = rsp.rfind("```")
        _start = rsp.find("```json")
        if _end != -1 and _start != -1:
            json_str = rsp[_start + len("```json") : _end].strip()
        else:
            json_str = rsp
        try:
            json_result = json.loads(json_str)
        except:
            return rsp
        return json_result
