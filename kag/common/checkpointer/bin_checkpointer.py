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
import shelve
import logging
import transaction
from ZODB import DB
from ZODB.FileStorage import FileStorage
from kag.common.checkpointer.base import CheckPointer

logger = logging.getLogger()


@CheckPointer.register("bin")
class BinCheckPointer(CheckPointer):
    """
    A subclass of CheckPointer that uses shelve for binary checkpoint management.

    This class extends the CheckPointer class to provide binary checkpoint
    management using the shelve module. It supports opening, reading, writing,
    and closing checkpoint files in a binary format.
    """

    def open(self):
        """
        Opens the checkpoint file using shelve in writeback mode.

        Returns:
            Any: The shelve object representing the checkpoint file.
        """
        return shelve.open(self._ckpt_file_path, "c", writeback=True)

    def exists(self, key):
        """
        Checks if a key exists in the checkpoint file.

        Args:
            key (str): The key to check for existence in the checkpoint.

        Returns:
            bool: True if the key exists in the checkpoint, False otherwise.
        """
        return key in self._ckpt

    def read_from_ckpt(self, key):
        """
        Reads a value from the checkpoint file using the specified key.

        Args:
            key (str): The key to retrieve the value from the checkpoint.

        Returns:
            Any: The value associated with the key in the checkpoint.
        """
        return self._ckpt[key]

    def write_to_ckpt(self, key, value):
        """
        Writes a value to the checkpoint file using the specified key.

        Args:
            key (str): The key to store the value in the checkpoint.
            value (Any): The value to be stored in the checkpoint.
        """
        self._ckpt[key] = value
        self._ckpt.sync()

    def close(self):
        """
        Closes the checkpoint file and ensures data is written to disk.
        """
        self._ckpt.sync()
        self._ckpt.close()


@CheckPointer.register("zodb")
class ZODBCheckPointer(CheckPointer):
    """
    A CheckPointer implementation that uses ZODB as the underlying storage.

    This class provides methods to open, read, write, and close checkpoints using ZODB.
    """

    def __init__(self, ckpt_dir: str, rank: int = 0, world_size: int = 1):
        """
        Initializes the ZODBCheckPointer with the given checkpoint directory, rank, and world size.

        Args:
            ckpt_dir (str): The directory where checkpoint files are stored.
            rank (int): The rank of the current process (default is 0).
            world_size (int): The total number of processes in the distributed environment (default is 1).
        """
        super().__init__(ckpt_dir, rank, world_size)

    def open(self):
        """
        Opens the ZODB database and returns the root object for checkpoint storage.

        Returns:
            dict: The root object of the ZODB database, which is a dictionary-like object.
        """

        storage = FileStorage(self._ckpt_file_path)
        self._db = DB(storage)
        self._connection = self._db.open()
        return self._connection.root()

    def read_from_ckpt(self, key):
        """
        Reads a value from the checkpoint using the specified key.

        Args:
            key (str): The key to retrieve the value from the checkpoint.

        Returns:
            Any: The value associated with the key in the checkpoint.
        """
        return self._ckpt.get(key, None)

    def write_to_ckpt(self, key, value):
        """
        Writes a value to the checkpoint using the specified key.

        Args:
            key (str): The key to store the value in the checkpoint.
            value (Any): The value to be stored in the checkpoint.
        """
        self._ckpt[key] = value
        try:
            transaction.commit()
        except Exception as e:
            transaction.abort()
            logger.warn(f"failed to write checkpoint {key} to db, info: {e}")

    def close(self):
        """
        Closes the ZODB database connection.
        """
        try:
            transaction.commit()
        except:
            transaction.abort()
        if self._connection is not None:
            self._connection.close()
        if self._db is not None:
            self._db.close()

    def exists(self, key):
        """
        Checks if a key exists in the checkpoint.

        Args:
            key (str): The key to check for existence in the checkpoint.

        Returns:
            bool: True if the key exists in the checkpoint, False otherwise.
        """
        return key in self._ckpt
