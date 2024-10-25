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
from kag.common.vectorizer.vectorizer import Vectorizer


class VectorizerConfigChecker(object):
    """
    Check whether the vectorizer config is valid.
    """

    def check(self, vectorizer_config: str) -> int:
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
        try:
            config = json.loads(vectorizer_config)
            vectorizer = Vectorizer.from_config(config)
            vector_dimensions = vectorizer.vector_dimensions
            return vector_dimensions
        except Exception as ex:
            message = "invalid vectorizer config: %s" % str(ex)
            raise RuntimeError(message) from ex
