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
import numpy as np
from typing import List, Union, Any
from kag.builder.model.sub_graph import Node, SubGraph
from kag.common.registry import Registrable
from kag.interface.builder.base import BuilderComponent
from knext.common.base.runnable import Input, Output


class MatchConfig(Registrable):
    """
    Configuration class for matching operations.

    This class is used to define the parameters for matching operations, such as the number of matches to return,
    the labels to consider, and the threshold for matching confidence.

    Attributes:
        k (int): The number of matches to return. Defaults to 1.
        labels (List[str]): The list of labels to consider for matching. Defaults to None.
        threshold (float): The confidence threshold for matching. Defaults to 0.9.
    """

    def __init__(self, k: int = 1, labels: List[str] = None, threshold: float = 0.9):
        """
        Initializes the MatchConfig with the specified parameters.

        Args:
            k (int, optional): The number of matches to return. Defaults to 1.
            labels (List[str], optional): The list of labels to consider for matching. Defaults to None.
            threshold (float, optional): The confidence threshold for matching. Defaults to 0.9.
        """
        self.k = k
        self.labels = labels
        self.threshold = threshold


MatchConfig.register("base", as_default=True)(MatchConfig)


class ExternalGraphLoaderABC(BuilderComponent):
    """
    Abstract base class for loading and interacting with external knowledge graphs.

    This class defines the interface for components that load and interact with external knowledge graphs.
    It inherits from `BuilderComponent` and provides methods for dumping subgraphs, performing named entity
    recognition (NER), retrieving allowed labels, and matching entities.

    """

    def __init__(self, match_config: MatchConfig, **kwargs):
        """
        Initializes the ExternalGraphLoaderABC with the specified match configuration.

        Args:
            match_config (MatchConfig): The configuration for matching operations.
        """
        super().__init__(**kwargs)
        self.match_config = match_config

    def dump(self) -> List[SubGraph]:
        """
        Abstract method to dump subgraphs from the external knowledge graph.

        Returns:
            List[SubGraph]: A list of subgraphs extracted from the external knowledge graph.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("dump not implemented yet.")

    def ner(self, content: str) -> List[Node]:
        """
        Abstract method to perform named entity recognition (NER) on the given content based on the external graph nodes.

        Args:
            content (str): The content to perform NER on.

        Returns:
            List[Node]: A list of nodes representing the recognized entities.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("ner not implemented yet.")

    def get_allowed_labels(self, labels: List[str] = None) -> List[str]:
        """
        Abstract method to obtain the allowed labels during matching, which are the intersection of the node labels in the external graph and the `labels` argument.

        Args:
            labels (List[str], optional): The list of labels to filter by. Defaults to None.

        Returns:
            List[str]: A list of allowed labels.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("get_allowed_labels not implemented yet.")

    def match_entity(
        self,
        query: Union[str, List[float], np.ndarray],
    ):
        """
        Method to match entities based on the given query.

        Args:
            query (Union[str, List[float], np.ndarray]): The query to match entities against.
                This can be a string, a list of floats, or a numpy array.
        Returns:
            Nodes in the graph that match the entity.
        """

    @property
    def input_types(self):
        return Any

    @property
    def output_types(self):
        return SubGraph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the component to process input data and return a list of subgraphs.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        return self.dump()
