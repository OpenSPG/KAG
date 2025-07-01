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
import json
from kag.common.checkpointer.base import CheckPointer


@CheckPointer.register("txt")
class TxtCheckPointer(CheckPointer):
    """
    A subclass of CheckPointer that uses a text file for checkpoint management.

    This class extends the CheckPointer class to provide checkpoint management
    using a text file. It supports opening, reading, writing, and closing
    checkpoint files in a text format. Each checkpoint entry is stored as a
    JSON object in the file.
    """

    def open(self):
        """
        Opens the checkpoint file and loads existing data into a dictionary.

        Returns:
            dict: A dictionary containing the checkpoint data.
        """
        ckpt = {}
        if os.path.exists(self._ckpt_file_path):
            with open(
                self._ckpt_file_path, "r", encoding="utf-8", newline="\n"
            ) as reader:
                for line in reader:
                    data = json.loads(line)
                    ckpt[data["id"]] = data["value"]
        self._writer = open(self._ckpt_file_path, "a", encoding="utf-8", newline="\n")
        return ckpt

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
        self._writer.write(json.dumps({"id": key, "value": value}, ensure_ascii=False))
        self._writer.write("\n")
        self._writer.flush()

    def _close(self):
        """
        Closes the checkpoint file and ensures data is written to disk.
        """
        self._writer.flush()
        self._writer.close()

    def size(self):
        return len(self._ckpt)

    def keys(self):
        return set(self._ckpt.keys())
