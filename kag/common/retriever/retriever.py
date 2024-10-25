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
from typing import Any, Union, Iterable, Tuple

from typing import Dict
import logging

logger = logging.getLogger(__name__)

Item = Dict[str, Any]
RetrievalResult = Iterable[Tuple[Item, float]]


class Retriever(ABC):
    """
    Retriever indexing a collection of items and supports fast retrieving of the
    desired items given a query.
    """

    @classmethod
    def from_config(cls, config: Union[str, Path, Dict[str, Any]]) -> "Retriever":
        """
        Create retriever from `config`.

        If `config` is a string or path, it will be loaded as a dictionary depending
        on its file extension. Currently, the following formats are supported:

        * .json: JSON
        * .json5: JSON with comments support
        * .yaml: YAML

        :param config: retriever config
        :type config: str, Path or Dict[str, Any]
        :return: retriever instance
        :rtype: Retriever
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
                message += "can not load retriever config from %r" % str(config_path)
                raise RuntimeError(message)
        elif isinstance(config, dict):
            pass
        else:
            message = "only str, Path and dict are supported; "
            message += "invalid retriever config: %r" % (config,)
            raise RuntimeError(message)

        class_name = config.get("retriever")
        if class_name is None:
            message = "retriever class name is not specified"
            raise RuntimeError(message)
        retriever_class = dynamic_import_class(class_name, "retriever")
        if not issubclass(retriever_class, Retriever):
            message = "class %r is not a retriever class" % (class_name,)
            raise RuntimeError(message)
        retriever = retriever_class._from_config(config)
        return retriever

    @classmethod
    @abstractmethod
    def _from_config(cls, config: Dict[str, Any]) -> "Retriever":
        """
        Create retriever from `config`. This method is supposed to be implemented
        by derived classes.

        :param config: retriever config
        :type config: Dict[str, Any]
        :return: retriever instance
        :rtype: Retriever
        """
        message = "abstract method _from_config is not implemented"
        raise NotImplementedError(message)

    def index(self, items: Union[Item, Iterable[Item]]) -> None:
        """
        Add one or more items to the index of the retriever.

        NOTE: This method may not be supported by the retriever.

        :param items: items to index
        :type items: Item or Iterable[Item]
        """
        message = "method index is not supported by the retriever"
        raise RuntimeError(message)

    @abstractmethod
    def retrieve(
            self, queries: Union[str, Iterable[str]], top_k: int = 10
    ) -> Union[RetrievalResult, Iterable[RetrievalResult]]:
        """
        Retrieve items for the given query or queries.

        :param queries: queries to retrieve
        :type queries: str or Iterable[str]
        :param int top_k: how many most related items to return for each query, default to 10
        :return: retrieval results of the queries
        :rtype: RetrievalResult or Iterable[RetrievalResult]
        """
        message = "abstract method retrieve is not implemented"
        raise NotImplementedError(message)


