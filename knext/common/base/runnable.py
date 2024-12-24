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

from typing import TypeVar, Type, List

Other = TypeVar("Other")

Input = TypeVar("Input", contravariant=True)
Output = TypeVar("Output", covariant=True)


class Runnable:
    """
    Abstract base class that can be invoked synchronously.
    """

    _last: bool = False

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """Transform an input into an output sequence synchronously."""
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )

    def batch(self, inputs: List[Input], **kwargs) -> List[Output]:
        """Transform inputs into an output sequence synchronously."""
        raise NotImplementedError(
            f"`batch` is not currently supported for {self.__class__.__name__}."
        )

    def __rshift__(self, other):
        """
        Overloads the right shift operator (>>) for the Chain class.

        This method allows for chaining together Components and Chains using the
        right shift operator. It takes an input `other`, which can be a single
        Component, a list of Components, a single Chain, or a list of Chains.

        The process is as follows:
        - If `other` is None or an empty value, the original Chain instance (`self`)
        is returned.
        - If `other` is not a list, it is converted into a list containing a single
        element.
        - For each element in `other`, a directed acyclic graph (DAG) is created:
        - If the element is a Component, it is added to the DAG and an edge is created
        from the current Chain (`self`) to the Component.
        - If the element is a Chain, the method finds the end nodes of the current
        DAG and the start nodes of the Chain's DAG to create appropriate edges
        between them. The two DAGs are then combined.
        - After processing all elements in `other`, all DAGs are combined into a final
        DAG using `nx.compose_all`.
        - A new Chain object is created and returned, initialized with the final combined DAG.

        Args:
        other: A Chain, list of Chains, Component, list of Components, or None
        representing the elements to chain with the current instance.

        Returns:
        A new Chain object that represents the combined DAG of the current instance
        and the provided elements.
        """
        raise NotImplementedError(
            f"`__rshift__` is not currently supported for {self.__class__.__name__}."
        )

    def _check_type(self, other: Other) -> bool:
        pass
