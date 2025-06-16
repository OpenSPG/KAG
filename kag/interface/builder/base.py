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
import concurrent
import copy
from typing import List, Any, Union
from functools import partial
from knext.common.base.component import Component
from knext.common.base.runnable import Input, Output
from kag.common.registry import Registrable
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.checkpointer import CheckPointer, CheckpointerManager
from kag.common.sharding_info import ShardingInfo
from kag.common.utils import generate_hash_id


class BuilderComponentData:
    def __init__(self, data: Any, hash_key: str = None, suffix: str = ""):
        self.data = data
        if not hash_key:
            hash_key = self.get_object_hash_key(self.data)
        self.hash_key = f"{hash_key}->{suffix}"

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
    """
    Abstract base class for all builder component.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        self.language = kwargs.get("language", self.kag_project_config.language)
        rank = kwargs.get("rank")
        world_size = kwargs.get("world_size")
        if rank is None or world_size is None:
            from kag.common.env import get_rank, get_world_size

            rank = get_rank(0)
            world_size = get_world_size(1)
        self.sharding_info = ShardingInfo(shard_id=rank, shard_count=world_size)

        self._checkpointer_initialized = False

    @property
    def checkpointer(self):
        if not self._checkpointer_initialized:
            if self.ckpt_subdir:
                self.ckpt_dir = os.path.join(
                    self.kag_project_config.ckpt_dir, self.ckpt_subdir
                )
                self._checkpointer: CheckPointer = CheckpointerManager.get_checkpointer(
                    {
                        "type": "diskcache",
                        "ckpt_dir": self.ckpt_dir,
                        "rank": self.sharding_info.get_rank(),
                        "world_size": self.sharding_info.get_world_size(),
                    }
                )

            else:
                self._checkpointer = None
            self._checkpointer_initialized = True
        return self._checkpointer

    @property
    def type(self):
        """
        Get the type label of the object.

        Returns:
            str: The type label of the object, fixed as "BUILDER".
        """
        return "BUILDER"

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return str

    @property
    def ckpt_subdir(self):
        return type(self).__name__

    @property
    def inherit_input_key(self):
        return True

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to be implemented by subclasses for build component.

        Args:
            input (Input): The chunk to be split.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of smaller chunks resulting from the split operation.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )

    def invoke(
        self, input: Input, **kwargs
    ) -> List[Union[Output, BuilderComponentData]]:
        if not isinstance(input, BuilderComponentData):
            input = BuilderComponentData(input)

        input_data = input.data
        input_key = input.hash_key

        if self.inherit_input_key:
            output_key = input_key
        else:
            output_key = None
        suffix = type(self).__name__
        write_ckpt = kwargs.get("write_ckpt", True)
        if write_ckpt and self.checkpointer:
            # found existing data in checkpointer
            if input_key and self.checkpointer.exists(input_key):
                output = self.checkpointer.read_from_ckpt(input_key)
                if output is not None:
                    return [
                        BuilderComponentData(x, output_key, suffix=suffix)
                        for x in output
                    ]
            # not found
            output = self._invoke(input_data, **kwargs)
            if input_key:
                self.checkpointer.write_to_ckpt(input_key, output)
            return [BuilderComponentData(x, output_key, suffix=suffix) for x in output]

        else:
            output = self._invoke(input_data, **kwargs)
            return [BuilderComponentData(x, output_key, suffix=suffix) for x in output]

    async def _ainvoke(self, input: Input, **kwargs) -> List[Output]:
        """
        The asynchronous version of `_invoke` which is implemented by wrapping `_invoke` with `asyncio.to_thread` by default.

        Args:
            input (Input): The chunk to be split.
            **kwargs: Additional keyword arguments, currently unused but kept for potential future expansion.

        Returns:
            List[Output]: A list of smaller chunks resulting from the split operation.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        return await asyncio.to_thread(lambda: self._invoke(input, **kwargs))

    async def ainvoke(
        self, input: Input, **kwargs
    ) -> List[Union[Output, BuilderComponentData]]:
        if not isinstance(input, BuilderComponentData):
            input = BuilderComponentData(input)

        input_data = input.data
        input_key = input.hash_key

        if self.inherit_input_key:
            output_key = input_key
        else:
            output_key = None
        suffix = type(self).__name__
        write_ckpt = kwargs.get("write_ckpt", True)
        if write_ckpt and self.checkpointer:
            # found existing data in checkpointer
            if input_key and self.checkpointer.exists(input_key):
                output = await asyncio.to_thread(
                    lambda: self.checkpointer.read_from_ckpt(input_key)
                )

                if output is not None:
                    return [
                        BuilderComponentData(x, output_key, suffix=suffix)
                        for x in output
                    ]

            # not found
            output = await self._ainvoke(input_data, **kwargs)
            if input_key:
                await asyncio.to_thread(
                    lambda: self.checkpointer.write_to_ckpt(input_key, output)
                )
            return [BuilderComponentData(x, output_key, suffix=suffix) for x in output]

        else:
            output = await self._ainvoke(input_data, **kwargs)
            return [BuilderComponentData(x, output_key, suffix=suffix) for x in output]


class MPBuilderComponentWrapper(BuilderComponent):
    """Multiprocessing wrapper for CPU-bound BuilderComponent instances.

    This class wraps a BuilderComponent to execute its _invoke method in a
    separate process using a ProcessPoolExecutor. This is suitable for CPU-bound
    operations that can benefit from parallel execution.

    Attributes:
        max_workers (int): Maximum number of parallel worker processes.
        _executor (ProcessPoolExecutor): Process pool for parallel task execution.
        _obj (BuilderComponent): Wrapped component instance for main process access.
    """

    def __init__(
        self, component_config: dict, max_workers: int = os.cpu_count(), **kwargs
    ):
        """Initialize multiprocessing wrapper.

        Args:
            component_config (dict): Configuration dictionary for the wrapped component.
            max_workers (int, optional): Maximum number of parallel workers. Defaults to CPU count.
            **kwargs: Additional keyword arguments for base class initialization.

        """
        self.max_workers = max_workers
        component_config = dict(component_config)
        self._executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=MPBuilderComponentWrapper._init_worker,
            initargs=(
                self.get_cls(),
                component_config,
            ),
        )

        self._obj = self.get_cls().from_config(copy.deepcopy(component_config))
        super().__init__(**kwargs)

    def get_cls(self):
        """Abstract method to get the class of component to be wrapped.

        Returns:
            type: Class reference of the component to be parallelized.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("get_cls not implemented yet.")

    @staticmethod
    def _init_worker(cls, component_config):
        """Worker process initializer.

        Args:
            cls (type): Component class from get_cls()
            component_config (dict): Configuration for component instantiation

        Creates:
            PROCESS_COMPONENT (BuilderComponent): Component instance in worker process
        """
        global PROCESS_COMPONENT
        PROCESS_COMPONENT = cls.from_config(copy.deepcopy(component_config))

    @staticmethod
    def _invoke_in_worker(input, **kwargs):
        """Execute component processing in worker process.

        Args:
            input (Input): Input data for processing
            **kwargs: Additional arguments for component._invoke()

        Returns:
            List[Output]: Processing results from worker process
        """
        result = PROCESS_COMPONENT._invoke(input, **kwargs)
        return result

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """Synchronous execution wrapper.

        Args:
            input (Input): Input data for processing
            **kwargs: Additional arguments for component._invoke()

        Returns:
            List[Output]: Processing results from worker process
        """
        future = self._executor.submit(partial(self._invoke_in_worker, input, **kwargs))
        return future.result()

    async def _ainvoke(self, input: Input, **kwargs) -> List[Output]:
        """Asynchronous execution wrapper.

        Args:
            input (Input): Input data for processing
            **kwargs: Additional arguments for component._invoke()

        Returns:
            List[Output]: Processing results from worker process
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, partial(self._invoke_in_worker, input, **kwargs)
        )

    @property
    def input_types(self) -> Input:
        return self._obj.input_types

    @property
    def output_types(self) -> Output:
        return self._obj.output_types

    @property
    def ckpt_subdir(self):
        return self._obj.ckpt_subdir

    @property
    def inherit_input_key(self):
        return self._obj.inherit_input_key
