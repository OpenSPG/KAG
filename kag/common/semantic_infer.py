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


import regex as re
import os
import json
from typing import List, Dict
from collections import OrderedDict
from kag.common.llm.client.llm_client import LLMClient
from kag.common.base.prompt_op import PromptOp


class HyperGenPromptOp(PromptOp):

    template_en = (
        "A hypernym is a word that denotes a general category into which more specific words (hyponym words) fall. "
        "In other words, it's an umbrella term that can encompass a range of more specific terms.\n"
        "Please list a hyponym-hypernym sequence which starts with the given [start] word, and gives a short description of each words in the sequence.\n"
        "Your answer should be in JSON format with a \"sequence\" key contains hyponym-hypernym sequence as list of words, and a \"description\" key contains short description of each words in sequence as a dict\n"
        "[start]: {query}\n"
    )

    # _hyper_with_target = (
    #     "A hypernym is a word that denotes a general category into which more specific words (hyponym words) fall. "
    #     "In other words, it's an umbrella term that can encompass a range of more specific terms.\n"
    #     "Please list a hyponym-hypernym sequence which starts with the given [start] word and ends with [end] word, and gives a short description of each words in the sequence.\n"
    #     "Your answer should be in JSON format with a \"sequence\" key contains hyponym-hypernym sequence as list of words, and a \"description\" key contains short description of each words in sequence as a dict\n"
    #     "[start]: {query}\n"
    #     "[end]: {target}\n"
    # )

    def __init__(self, language='en') -> None:
        super().__init__(language=language)

    def build_prompt(self, variables: Dict[str, str]) -> str:
        query = variables["query"]
        if variables["context"]:
            query += " (from the context: %s)" % variables["context"]
        if variables.get("target"):
            raise NotImplementedError
        else:
            instruction = self.template.format(query=query)

        return instruction

    def parse_response(self, response, **kwargs):
        if isinstance(response, str):
            resp_body = re.search(r'\{(?:[^{}]|(?R))*\}', response)
            resp_body = resp_body.group() if resp_body else response
            try:
                resp_body = json.loads(resp_body)
            except json.decoder.JSONDecodeError:
                try:
                    # 添加缺失的逗号
                    resp_body = re.subn(r'"\s+(?![,\}\]])"', '","', resp_body)[0]
                    # 未转义的双引号
                    resp_body = re.subn(r'(?<=[\[,\{:])\s*"', '@*@*@', resp_body)[0]
                    resp_body = re.subn(r'"\s*(?=[\],\}:])', '@*@*@', resp_body)[0]
                    resp_body = resp_body.replace('"', '\\"').replace("@*@*@", "\"")
                    resp_body = json.loads(resp_body)
                except json.decoder.JSONDecodeError:
                    raise ValueError(f"response json decode error: {response}")
        elif isinstance(response, dict):
            resp_body = response
        else:
            raise ValueError
        resp_words = (
            resp_body["sequence"]
            if isinstance(resp_body["sequence"], list) else
            [i.strip() for i in resp_body["sequence"].split(',')]
        )
        word_desc = resp_body.get("description", {})
        hyper_sequence = [
            {"name": word, "desc": word_desc.get(word, "")}
            for word in resp_words
        ]
        return hyper_sequence


class SemanticEnhance:

    hyper_edge = "SemanticIsA"
    concept_label = 'SemanticConcept'

    def __init__(self, **kwargs):
        self.semantic_model = LLMClient.from_config(eval(os.getenv("KAG_LLM")))
        self._expand_cache = OrderedDict()
        self.max_cache_size = 10000

    def expand_semantic_concept(self, node: str, context: str = None, target: str = None) -> List[Dict]:
        if (node, context, target) in self._expand_cache:
            return self._expand_cache[(node, context, target)]
        else:
            hyper_names = self.semantic_model.invoke(
                {"query": node, "context": context, "target": target},
                HyperGenPromptOp(),
                with_json_parse=False
            )
            self._expand_cache[(node, context, target)] = hyper_names
            if len(self._expand_cache) > self.max_cache_size:
                self._expand_cache.popitem(last=False)
        return hyper_names
