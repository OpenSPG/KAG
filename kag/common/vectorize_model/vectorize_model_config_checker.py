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


class VectorizeModelConfigChecker:
    """
    A class that checks whether the vectorizer configuration is valid.

    This class provides a method to validate the vectorizer configuration and return the embedding vector dimensions if valid.
    """

    def check(self, vectorizer_config: str) -> int:
        """
        Checks the vectorizer configuration.

        If the configuration is valid, it returns the actual embedding vector dimensions.
        If the configuration is invalid, it raises a RuntimeError exception.

        Args:
            vectorizer_config (str): The vectorizer configuration to be checked.

        Returns:
            int: The embedding vector dimensions.

        Raises:
            RuntimeError: If the configuration is invalid.
        """
        try:
            config = json.loads(vectorizer_config)
            from kag.interface import VectorizeModelABC

            vectorizer = VectorizeModelABC.from_config(config)
            res = vectorizer.vectorize("hello")
            return len(res)
        except Exception as ex:
            message = "invalid vectorizer config: %s" % str(ex)
            raise RuntimeError(message) from ex
