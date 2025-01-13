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
import threading
from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, generate_hash_id


class CheckPointer(Registrable):
    """
    A class for managing checkpoints in a distributed environment.

    This class provides methods to open, read, write, and close checkpoint files.
    It is designed to handle checkpoints in a distributed setting, where multiple
    processes may be writing checkpoints in parallel.

    Attributes:
        ckpt_file_name (str): The format string for checkpoint file names.
    """

    ckpt_file_name = "kag_checkpoint_{}_{}.ckpt"

    def __init__(self, ckpt_dir: str, rank: int = 0, world_size: int = 1):
        """
        Initializes the CheckPointer with the given checkpoint directory, rank, and world size.

        Args:
            ckpt_dir (str): The directory where checkpoint files are stored.
            rank (int): The rank of the current process (default is 0).
            world_size (int): The total number of processes in the distributed environment (default is 1).
        """
        self._ckpt_dir = ckpt_dir
        if not os.path.exists(ckpt_dir):
            os.makedirs(ckpt_dir, exist_ok=True)
        self.rank = rank
        self.world_size = world_size
        self._ckpt_file_path = os.path.join(
            self._ckpt_dir, CheckPointer.ckpt_file_name.format(rank, world_size)
        )
        self._ckpt = self.open()
        self._closed = False
        if self.size() > 0:
            print(
                f"{bold}{red}Existing checkpoint found in {self._ckpt_dir}, with {self.size()} records.{reset}"
            )

    def open(self):
        """
        Opens the checkpoint file and returns the checkpoint object.

        Returns:
            Any: The checkpoint object, which can be used for reading and writing.
        """
        raise NotImplementedError("open not implemented yet.")

    def read_from_ckpt(self, key):
        """
        Reads a value from the checkpoint file using the specified key.

        Args:
            key (str): The key to retrieve the value from the checkpoint.

        Returns:
            Any: The value associated with the key in the checkpoint.
        """
        raise NotImplementedError("read_from_ckpt not implemented yet.")

    def write_to_ckpt(self, key, value):
        """
        Writes a value to the checkpoint file using the specified key.

        Args:
            key (str): The key to store the value in the checkpoint.
            value (Any): The value to be stored in the checkpoint.
        """
        raise NotImplementedError("write_to_ckpt not implemented yet.")

    def _close(self):
        """
        Closes the checkpoint file.
        """
        raise NotImplementedError("close not implemented yet.")

    def close(self):
        """
        Closes the checkpoint file.
        """
        if not self._closed:
            self._close()
            self._closed = True

    def exists(self, key):
        """
        Checks if a key exists in the checkpoint file.

        Args:
            key (str): The key to check for existence in the checkpoint.

        Returns:
            bool: True if the key exists in the checkpoint, False otherwise.
        """
        raise NotImplementedError("close not implemented yet.")

    def keys(self):
        """
        Returns the key set contained in the checkpoint file.

        Returns:
            set:  The key set contained in the checkpoint.
        """

        raise NotImplementedError("keys not implemented yet.")

    def size(self):
        """
        Return the number of records in the checkpoint file.

        Returns:
            int: the number of records in the checkpoint file.
        """

        raise NotImplementedError("size not implemented yet.")

    def __contains__(self, key):
        """
        Defines the behavior of the `in` operator for the object.
        Args:
            key (str): The key to check for existence in the checkpoint.

        Returns:
            bool: True if the key exists in the checkpoint, False otherwise.
        """

        return self.exists(key)


class CheckpointerManager:
    """
    Manages the lifecycle of CheckPointer objects.

    This class provides a thread-safe mechanism to retrieve and close CheckPointer
    instances based on a configuration. It uses a global dictionary to cache
    CheckPointer objects, ensuring that each configuration corresponds to a unique
    instance.
    """

    _CKPT_OBJS = {}
    _LOCK = threading.Lock()

    @staticmethod
    def get_checkpointer(config):
        """
        Retrieves or creates a CheckPointer instance based on the provided configuration.

        Args:
            config (dict): The configuration used to initialize the CheckPointer.

        Returns:
            CheckPointer: A CheckPointer instance corresponding to the configuration.
        """
        with CheckpointerManager._LOCK:
            key = generate_hash_id(config)
            if key not in CheckpointerManager._CKPT_OBJS:
                ckpter = CheckPointer.from_config(config)
                CheckpointerManager._CKPT_OBJS[key] = ckpter
            return CheckpointerManager._CKPT_OBJS[key]

    @staticmethod
    def close():
        """
        Closes all cached CheckPointer instances.

        This method iterates through all cached CheckPointer objects and calls their
        `close` method to release resources. After calling this method, the cache
        will be cleared.
        """
        with CheckpointerManager._LOCK:
            for v in CheckpointerManager._CKPT_OBJS.values():
                v.close()
            CheckpointerManager._CKPT_OBJS.clear()
