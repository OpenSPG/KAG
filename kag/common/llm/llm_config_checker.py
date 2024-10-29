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
from kag.common.llm.client import LLMClient


class LLMConfigChecker(object):
    """
    Check whether the vectorizer config is valid.
    """

    def check(self, config: str) -> int:
        """
        Check the vectorizer config.

        * If the config is valid, return the actual embedding vector dimensions.

        * If the config is invalid, raise a RuntimeError exception.

        :param vectorizer_config: vectorizer config
        :type vectorizer_config: str
        :return: embedding vector dimensions
        :rtype: int
        :raises RuntimeError: if the config is invalid
        """
        config = json.loads(config)
        llm_client = LLMClient.from_config(config)
        try:
            res = llm_client("who are you?")
            return len(res)
        except:
            raise RuntimeError("invalid llm config: %s" % config)
        
if __name__ == "__main__":
    config = '''
        {"client_type" :"ollama",
        "base_url" : "http://localhost:11434/api/generate",
        "model" : "llama3.1" }
    '''
    config_checker = LLMConfigChecker()
    res = config_checker.check(config)
