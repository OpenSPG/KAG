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
import threading
import pickle
from diskcache import Cache
import BTrees.OOBTree
from typing import Any
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

    def _close(self):
        """
        Closes the checkpoint file and ensures data is written to disk.
        """
        self._ckpt.sync()
        self._ckpt.close()

    def size(self):
        """
        Returns the number of entries in the checkpoint.
        Returns:
            int: The number of entries in the checkpoint.
        """

        return len(self._ckpt)

    def keys(self):
        return set(self._ckpt.keys())


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
        self._lock = threading.Lock()
        super().__init__(ckpt_dir, rank, world_size)

    def open(self):
        """
        Opens the ZODB database and returns the root object for checkpoint storage.

        Returns:
            dict: The root object of the ZODB database, which is a dictionary-like object.
        """
        with self._lock:
            storage = FileStorage(self._ckpt_file_path)
            db = DB(storage)
            with db.transaction() as conn:
                if not hasattr(conn.root, "data"):
                    conn.root.data = BTrees.OOBTree.BTree()
            return db

    def read_from_ckpt(self, key):
        """
        Reads a value from the checkpoint using the specified key.

        Args:
            key (str): The key to retrieve the value from the checkpoint.

        Returns:
            Any: The value associated with the key in the checkpoint.
        """
        with self._lock:
            with self._ckpt.transaction() as conn:
                obj = conn.root.data.get(key, None)
            if obj:
                return pickle.loads(obj)
            else:
                return None

    def write_to_ckpt(self, key, value):
        """
        Writes a value to the checkpoint using the specified key.
        By default, ZODB tracks modifications to the written object (value) and
        continuously synchronizes these changes to the storage. For example, if
        the value is a `SubGraph` object, subsequent modifications to its
        attributes will be synchronized, which is not what we expect.
        Therefore, we use `pickle` to serialize the value object before writing it,
        ensuring that the object behaves as an immutable object.

        Args:
            key (str): The key to store the value in the checkpoint.
            value (Any): The value to be stored in the checkpoint.
        """
        with self._lock:
            try:
                with self._ckpt.transaction() as conn:
                    conn.root.data[key] = pickle.dumps(value)
            except Exception as e:
                logger.warn(f"failed to write checkpoint {key} to db, info: {e}")

    def _close(self):
        """
        Closes the ZODB database connection.
        """
        with self._lock:
            try:
                transaction.commit()
            except:
                transaction.abort()
            if self._ckpt is not None:
                self._ckpt.close()

    def exists(self, key):
        """
        Checks if a key exists in the checkpoint.

        Args:
            key (str): The key to check for existence in the checkpoint.

        Returns:
            bool: True if the key exists in the checkpoint, False otherwise.
        """
        with self._lock:
            with self._ckpt.transaction() as conn:
                return key in conn.root.data

    def size(self):
        """
        Returns the number of entries in the checkpoint.

        This method calculates the size of the checkpoint by counting the number
        of keys stored in the checkpoint's data dictionary. It ensures thread-safe
        access to the checkpoint by using a lock.

        Returns:
            int: The number of entries in the checkpoint.
        """
        with self._lock:
            with self._ckpt.transaction() as conn:
                return len(conn.root.data)

    def keys(self):
        with self._lock:
            with self._ckpt.transaction() as conn:
                return set(conn.root.data.keys())


@CheckPointer.register("diskcache")
class DiskCacheCheckPointer(CheckPointer):
    def __init__(self, ckpt_dir: str, rank: int = 0, world_size: int = 1):
        self._lock = threading.Lock()
        super().__init__(ckpt_dir, rank, world_size)

    def open(self):
        return Cache(
            directory=self._ckpt_dir,
            shards=8,
            timeout=60,
            size_limit=1e12,
            disk_min_file_size=1024**2,
        )

    def write_to_ckpt(self, key: str, value: Any):
        self._ckpt.set(key, value, retry=True)

    def read_from_ckpt(self, key: str) -> Any:
        return self._ckpt.get(key, default=None, retry=True)

    def exists(self, key):
        return key in self._ckpt

    def size(self):
        return len(self._ckpt)

    def keys(self):
        return list(self._ckpt.iterkeys())

    def _close(self):
        with self._lock:
            self._ckpt.close()
