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


class LLMConfigChecker(object):
    """
    Check whether the llm config is valid.
    """

    def check(self, config: str) -> str:
        """
        Check the llm config.

        * If the config is valid, return the generated text.

        * If the config is invalid, raise a RuntimeError exception.

        :param config: llm config
        :type config: str
        :return: the generated text
        :rtype: str
        :raises RuntimeError: if the config is invalid
        """
        from kag.interface import LLMClient

        config = json.loads(config)
        llm_client = LLMClient.from_config(config)
        try:
            res = llm_client("who are you?")
            return res
        except Exception as ex:
            raise RuntimeError(f"invalid llm config: {config}, for details: {ex}")


if __name__ == "__main__":
    config = """
        {"client_type" :"ollama",
        "base_url" : "http://localhost:11434/",
        "model" : "llama3.1" }
    """
    config_checker = LLMConfigChecker()
    res = config_checker.check(config)
