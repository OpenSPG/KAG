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

import os
import asyncio
from typing import List, Any, Union

from knext.common.base.component import Component
from knext.common.base.runnable import Input, Output
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.checkpointer import CheckPointer, CheckpointerManager
from kag.common.sharding_info import ShardingInfo
from kag.common.utils import generate_hash_id


class BuilderComponentData:
    def __init__(self, data: Any, hash_key: str = None):
        self.data = data
        if not hash_key:
            hash_key = self.get_object_hash_key(self.data)
        self.hash_key = hash_key

    def get_object_hash_key(self, input_object):
        if hasattr(input_object, "hash_key"):
            return getattr(input_object, "hash_key")
        return generate_hash_id(input_object)

    def to_dict(self):
        if hasattr(self.data, "to_dict"):
            return self.data.to_dict()
        raise NotImplementedError(
            f"data type {type(self.data)} do not implemente method `to_dict`."
        )


@Registrable.register("builder")
class BuilderComponent(Component, Registrable):
    """Abstract base class for all builder components.

    Provides synchronous/asynchronous processing methods with checkpoint management.
    Subclasses must implement core processing logic in _invoke and related methods.

    Attributes:
        language (str): Language configuration for the component.
        sharding_info (ShardingInfo): Information about distributed sharding.
        checkpointer (CheckPointer, optional): Checkpoint manager instance if configured.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the builder component with environment configurations.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments. Recognized parameters:
                language (str): Language configuration (default from KAG_PROJECT_CONF)
                rank (int): Distributed shard ID (auto-detected if None)
                world_size (int): Total shard count (auto-detected if None)
        """

        super().__init__(*args, **kwargs)
        self.language = kwargs.get("language", KAG_PROJECT_CONF.language)
        self.batch_size = int(kwargs.get("batch_size", 1))
        rank = kwargs.get("rank")
        world_size = kwargs.get("world_size")
        if rank is None or world_size is None:
            from kag.common.env import get_rank, get_world_size

            rank = get_rank(0)
            world_size = get_world_size(1)
        self.sharding_info = ShardingInfo(shard_id=rank, shard_count=world_size)

        if self.ckpt_subdir:
            self.ckpt_dir = os.path.join(KAG_PROJECT_CONF.ckpt_dir, self.ckpt_subdir)

            self.checkpointer: CheckPointer = CheckpointerManager.get_checkpointer(
                {
                    "type": "zodb",
                    "ckpt_dir": self.ckpt_dir,
                    "rank": rank,
                    "world_size": world_size,
                }
            )
        else:
            self.checkpointer = None

    @property
    def type(self):
        """
        Get the type label of the object.

        Returns:
            str: The type label of the object, fixed as "BUILDER".
        """
        return "BUILDER"

    @property
    def ckpt_subdir(self):
        """str, optional: Subdirectory path for checkpoint storage. None disables checkpoints."""
        return None

    @property
    def inherit_input_key(self):
        """bool: Flag indicating whether output inherits input's hash key (default True)."""
        return True

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """Core synchronous processing logic to be implemented by subclasses.

        Args:
            input (Input): Input data for processing
            **kwargs: Additional implementation-specific arguments

        Returns:
            List[Output]: Processed output objects

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """

        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )

    def _batch_invoke(self, input: List[Input], **kwargs) -> List[List[Output]]:
        """Core batch processing logic to be implemented by subclasses,
        defaults to call _invoke sequentially.

        Args:
            input (List[Input]): Batch of input data items
            **kwargs: Additional parameters (see invoke())

        Returns:
            List[List[Output]]: List of output lists corresponding to each input item
        """
        output = []
        for item in input:
            output.append(self._invoke(item))
        return output

    def invoke(
        self, input: List[Input], **kwargs
    ) -> List[List[Union[Output, BuilderComponentData]]]:
        """Synchronous batch processing with checkpoint management.

        Args:
            inputs (List[Input]): Batch of input data items
            **kwargs: Additional parameters (see invoke())

        Returns:
            List[List[Output]]: List of output lists corresponding to each input item
        """

        input = [
            x if isinstance(x, BuilderComponentData) else BuilderComponentData(x)
            for x in input
        ]

        input_data = [x.data for x in input]
        input_keys = [x.hash_key for x in input]

        if self.inherit_input_key:
            output_keys = input_keys
        else:
            output_keys = [None] * len(input_keys)

        result = {}
        write_ckpt = kwargs.get("write_ckpt", True)
        not_found = []
        if write_ckpt and self.checkpointer:
            for idx, k in enumerate(input_keys):
                if k and self.checkpointer.exists(k):
                    output = self.checkpointer.read_from_ckpt(k)
                    result[idx] = output
                else:
                    not_found.append(idx)
            batched_output = self._batch_invoke([input_data[x] for x in not_found])
            for idx, output in zip(not_found, batched_output):
                result[idx] = output
                if input_keys[idx]:
                    self.checkpointer.write_to_ckpt(input_keys[idx], output)
            outputs = []
            for idx in range(len(input)):
                output_key = output_keys[idx]
                outputs.append(
                    [BuilderComponentData(x, output_key) for x in result[idx]]
                )
            return outputs
        else:
            outputs = []
            result = self._batch_invoke(input_data)
            for idx in range(len(input)):
                output_key = output_keys[idx]
                outputs.append(
                    [BuilderComponentData(x, output_key) for x in result[idx]]
                )
            return outputs

    async def _ainvoke(self, input: Input, **kwargs) -> List[Output]:
        """Asynchronous processing function, defaults to a to_thread wrapper for _invoke

        Args:
            input (Input): Input data for processing
            **kwargs: Additional implementation-specific arguments

        Returns:
            List[Output]: Processed output objects
        """

        return await asyncio.to_thread(lambda: self._invoke(input, **kwargs))

    async def _abatch_invoke(self, input: List[Input], **kwargs) -> List[List[Output]]:
        """Asynchronous batch processing logic, defaults to call _ainvoke concurrently.
        Args:
            input (List[Input]): Batch of input data items
            **kwargs: Additional parameters (see invoke())

        Returns:
            List[List[Output]]: List of output lists corresponding to each input item
        """

        tasks = [asyncio.create_task(self._ainvoke(x)) for x in input]
        outputs = await asyncio.gather(*tasks)
        return outputs

    async def ainvoke(
        self, input: List[Input], **kwargs
    ) -> List[List[Union[Output, BuilderComponentData]]]:
        """Asynchronous batch processing with checkpoint management.

        Args:
            input (List[Input]): Batch of input data items
            **kwargs: Additional parameters (see invoke())

        Returns:
            List[List[Output]]: List of output lists corresponding to each input item
        """
        input = [
            x if isinstance(x, BuilderComponentData) else BuilderComponentData(x)
            for x in input
        ]

        input_data = [x.data for x in input]
        input_keys = [x.hash_key for x in input]

        if self.inherit_input_key:
            output_keys = input_keys
        else:
            output_keys = [None] * len(input_keys)

        result = {}
        write_ckpt = kwargs.get("write_ckpt", True)
        not_found = []
        if write_ckpt and self.checkpointer:
            for idx, k in enumerate(input_keys):
                if k and self.checkpointer.exists(k):
                    output = await asyncio.to_thread(
                        lambda: self.checkpointer.read_from_ckpt(k)
                    )
                    result[idx] = output
                else:
                    not_found.append(idx)
            batched_output = await self._abatch_invoke(
                [input_data[x] for x in not_found]
            )

            for idx, output in zip(not_found, batched_output):
                result[idx] = output
                if input_keys[idx]:
                    await asyncio.to_thread(
                        lambda: self.checkpointer.write_to_ckpt(input_keys[idx], output)
                    )
            outputs = []
            for idx in range(len(input)):
                output_key = output_keys[idx]
                outputs.append(
                    [BuilderComponentData(x, output_key) for x in result[idx]]
                )
            return outputs
        else:
            outputs = []
            result = await self._abatch_invoke(input_data)
            for idx in range(len(input)):
                output_key = output_keys[idx]
                outputs.append(
                    [BuilderComponentData(x, output_key) for x in result[idx]]
                )
            return outputs
