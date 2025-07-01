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

from kag.builder.model.chunk import Chunk
from kag.interface import SplitterABC


class BaseTableSplitter(SplitterABC):
    """
    A base class for splitting table data into smaller chunks.

    This class inherits from SplitterABC and provides the functionality to split table data
    represented in markdown format into smaller chunks.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def split_table(self, org_chunk: Chunk, chunk_size: int = 2000, sep: str = "\n"):
        """
        Splits a markdown format table into smaller markdown tables.

        Args:
            org_chunk (Chunk): The original chunk containing the table data.
            chunk_size (int): The maximum size of each smaller chunk. Defaults to 2000.
            sep (str): The separator used to join the table rows. Defaults to "\n".

        Returns:
            List[Chunk]: A list of smaller chunks resulting from the split operation.
        """
        try:
            return self._split_table(
                org_chunk=org_chunk, chunk_size=chunk_size, sep=sep
            )
        except Exception:
            return None

    def _split_table(self, org_chunk: Chunk, chunk_size: int = 2000, sep: str = "\n"):
        """
        Internal method to split a markdown format table into smaller markdown tables.

        Args:
            org_chunk (Chunk): The original chunk containing the table data.
            chunk_size (int): The maximum size of each smaller chunk. Defaults to 2000.
            sep (str): The separator used to join the table rows. Defaults to "\n".

        Returns:
            List[Chunk]: A list of smaller chunks resulting from the split operation.
        """
        output = []
        content = org_chunk.content
        table_start = content.find("|")
        table_end = content.rfind("|") + 1
        if table_start is None or table_end is None or table_start == table_end:
            return None
        prefix = content[0:table_start].strip("\n ")
        table_rows = content[table_start:table_end].split("\n")
        table_header = table_rows[0]
        table_header_segmentation = table_rows[1]
        suffix = content[table_end:].strip("\n ")

        splitted = []
        cur = [prefix, table_header, table_header_segmentation]
        cur_len = len(prefix)
        for idx, row in enumerate(table_rows[2:]):
            if cur_len > chunk_size:
                cur.append(suffix)
                splitted.append(cur)
                cur_len = 0
                cur = [prefix, table_header, table_header_segmentation]
            cur.append(row)
            cur_len += len(row)

        cur.append(content[table_end:])
        if len(cur) > 0:
            splitted.append(cur)

        output = []
        for idx, sentences in enumerate(splitted):
            chunk = Chunk(
                id=f"{org_chunk.id}#{chunk_size}#table#{idx}#LEN",
                name=f"{org_chunk.name}#{idx}",
                content=sep.join(sentences),
                type=org_chunk.type,
                **org_chunk.kwargs,
            )
            output.append(chunk)
        return output
