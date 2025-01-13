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
from typing import List, Dict

from knext.common.base.component import Component
from knext.common.base.runnable import Input, Output
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.checkpointer import CheckPointer, CheckpointerManager
from kag.common.sharding_info import ShardingInfo


@Registrable.register("builder")
class BuilderComponent(Component, Registrable):
    """
    Abstract base class for all builder component.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = kwargs.get("language", KAG_PROJECT_CONF.language)
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

    def batch(self, inputs: List[Input], **kwargs) -> List[Output]:
        results = []
        for input in inputs:
            results.extend(self.invoke(input, **kwargs))
        return results

    def _handle(self, input: Dict) -> List[Dict]:
        _input = self.input_types.from_dict(input) if isinstance(input, dict) else input
        _output = self.invoke(_input)
        return [_o.to_dict() for _o in _output if _o]

    @property
    def ckpt_subdir(self):
        return None

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Abstract method to be implemented by subclasses for splitting a chunk.

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

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        write_ckpt = kwargs.get("write_ckpt", True)
        if write_ckpt and self.checkpointer:
            input_key = kwargs.get("key")
            # found existing data in checkpointer
            if input_key and self.checkpointer.exists(input_key):
                out = self.checkpointer.read_from_ckpt(input_key)
                if out is not None:
                    return out
            # not found
            output = self._invoke(input, **kwargs)
            if input_key:
                self.checkpointer.write_to_ckpt(input_key, output)
            return output
        else:
            return self._invoke(input, **kwargs)
