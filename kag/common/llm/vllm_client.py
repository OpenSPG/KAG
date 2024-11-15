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
import requests
from kag.common.llm.llm_client import LLMClient


# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@LLMClient.register("vllm")
class VLLMClient(LLMClient):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self.param = {}

    def sync_request(self, prompt):
        # import pdb; pdb.set_trace()
        self.param["messages"] = prompt
        self.param["model"] = self.model

        response = requests.post(
            self.base_url,
            data=json.dumps(self.param),
            headers={"Content-Type": "application/json"},
        )

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        content = content.replace("&rdquo;", "”").replace("&ldquo;", "“")
        content = content.replace("&middot;", "")
        return content

    def __call__(self, prompt):
        content = [{"role": "user", "content": prompt}]
        return self.sync_request(content)

    def call_with_json_parse(self, prompt):
        content = [{"role": "user", "content": prompt}]
        rsp = self.sync_request(content)
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
