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
from kag.common.registry import Registrable


class SolverPipelineABC(Registrable):
    """Base class for solver pipelines.

    This abstract base class defines the interface for solver pipeline implementations.
    Subclasses must implement the `invoke` and `ainvoke` methods to provide concrete
    execution logic.
    """

    def __init__(self):
        """Initializes the solver pipeline base class."""
        pass

    def invoke(self, query, **kwargs):
        """Executes the solver pipeline synchronously.

        Args:
            query: Input query or data to be processed by the pipeline.
            **kwargs: Additional keyword arguments for pipeline execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("invoke not implemented yet.")

    async def ainvoke(self, query, **kwargs):
        """Executes the solver pipeline asynchronously.

        Args:
            query: Input query or data to be processed by the pipeline.
            **kwargs: Additional keyword arguments for pipeline execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("ainvoke not implemented yet.")
