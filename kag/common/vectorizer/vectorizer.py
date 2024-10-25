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

import io
import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Union, Iterable, Optional, Dict

EmbeddingVector = Iterable[float]


class Vectorizer(ABC):
    """
    Vectorizer turns texts into embedding vectors.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._vector_dimensions = None

    @classmethod
    def from_config(cls, config: Union[str, Path, Dict[str, Any]]) -> "Vectorizer":
        """
        Create vectorizer from `config`.

        If `config` is a string or path, it will be loaded as a dictionary depending
        on its file extension. Currently, the following formats are supported:

        * .json: JSON
        * .json5: JSON with comments support
        * .yaml: YAML

        :param config: vectorizer config
        :type config: str, Path or Dict[str, Any]
        :return: vectorizer instance
        :rtype: Vectorizer
        """
        from kag.common.utils import dynamic_import_class

        if isinstance(config, (str, Path)):
            config_path = config
            if not isinstance(config_path, Path):
                config_path = Path(config_path)
            if config_path.name.endswith(".yaml"):
                import yaml

                with io.open(config_path, "r", encoding="utf-8") as fin:
                    config = yaml.safe_load(fin)
            elif config_path.name.endswith(".json5"):
                import json5

                with io.open(config_path, "r", encoding="utf-8") as fin:
                    config = json5.load(fin)
            elif config_path.name.endswith(".json"):
                with io.open(config_path, "r", encoding="utf-8") as fin:
                    config = json.load(fin)
            else:
                message = "only .json, .json5 and .yaml are supported currently; "
                message += "can not load vectorizer config from %r" % str(config_path)
                raise RuntimeError(message)
        elif isinstance(config, dict):
            pass
        else:
            message = "only str, Path and dict are supported; "
            message += "invalid vectorizer config: %r" % (config,)
            raise RuntimeError(message)

        class_name = config.get("vectorizer")
        if class_name is None:
            message = "vectorizer class name is not specified"
            raise RuntimeError(message)
        vectorizer_class = dynamic_import_class(class_name, "vectorizer")
        if not issubclass(vectorizer_class, Vectorizer):
            message = "class %r is not a vectorizer class" % (class_name,)
            raise RuntimeError(message)
        vectorizer = vectorizer_class._from_config(config)
        return vectorizer

    @classmethod
    @abstractmethod
    def _from_config(cls, config: Dict[str, Any]) -> "Vectorizer":
        """
        Create vectorizer from `config`. This method is supposed to be implemented
        by derived classes.

        :param config: vectorizer config
        :type config: Dict[str, Any]
        :return: vectorizer instance
        :rtype: Vectorizer
        """
        message = "abstract method _from_config is not implemented"
        raise NotImplementedError(message)

    def _get_vector_dimensions(self, config: Dict[str, Any]) -> Optional[int]:
        """
        Get embedding vector dimensions from `config`.

        * If vector dimensions is not specified in `config`, return None.

        * If vector dimensions is specified in `config` but not a positive integer,
          raise an exception.

        :param config: vectorizer config
        :type config: Dict[str, Any]
        :return: embedding vector dimensions or None
        :rtype: Optional[int]
        """
        value = config.get("vector_dimensions")
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError as ex:
                message = "vector_dimensions must be integer; "
                message += "%r is invalid" % (value,)
                raise RuntimeError(message) from ex
        if not isinstance(value, int) or value <= 0:
            message = "vector_dimensions must be positive-integer; "
            message += "%r is invalid" % (value,)
            raise RuntimeError(message)
        return value

    @property
    def vector_dimensions(self):
        """
        Dimension of generated embedding vectors.
        """
        if self._vector_dimensions is not None:
            return self._vector_dimensions
        try:
            example_input = "This is a test."
            example_vector = self.vectorize(example_input)
        except Exception as ex:
            message = "the embedding service is not available"
            raise RuntimeError(message) from ex
        value = self._get_vector_dimensions(self._config)
        if value is not None and value != len(example_vector):
            message = "invalid 'vector_dimensions', specified %d; " % value
            message += "but the actual generated embedding vector is of %d dimensions" % len(example_vector)
            raise RuntimeError(message)
        self._vector_dimensions = len(example_vector)
        return self._vector_dimensions

    @abstractmethod
    def vectorize(self, texts: Union[str, Iterable[str]]) -> Union[EmbeddingVector, Iterable[EmbeddingVector]]:
        """
        Vectorize a text string into an embedding vector or multiple text strings into
        multiple embedding vectors.

        :param texts: texts to vectorize
        :type texts: str or Iterable[str]
        :return: embedding vectors of the texts
        :rtype: EmbeddingVector or Iterable[EmbeddingVector]
        """
        message = "abstract method vectorize is not implemented"
        raise NotImplementedError(message)
