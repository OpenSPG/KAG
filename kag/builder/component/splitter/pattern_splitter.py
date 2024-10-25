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

from typing import Type, List, Union
import re
import os

from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.interface.builder.splitter_abc import SplitterABC
from knext.common.base.runnable import Input, Output


class PatternSplitter(SplitterABC):
    def __init__(self, pattern_dict: dict = None, chunk_cut_num=None):
        """
        pattern_dict:
        {
            "pattern": 匹配pattern,
            "group": {
                "header":1,
                "name":2,
                "content":3
            }
        }
        """
        super().__init__()
        if pattern_dict is None:
            pattern_dict = {
                "pattern": r"(\d+)\.([^0-9]+?)？([^0-9第版].*?)(?=\d+\.|$)",
                "group": {"header": 2, "name": 2, "content": 0},
            }
        self.pattern = pattern_dict["pattern"]
        self.group = pattern_dict["group"]
        self.chunk_cut_num = chunk_cut_num

    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return List[Chunk]

    def split_sentence(self, content):
        sentence_delimiters = "。？?！!；;\n"
        output = []
        start = 0
        for idx, char in enumerate(content):
            if char in sentence_delimiters:
                end = idx
                tmp = content[start : end + 1].strip()
                if len(tmp) > 0:
                    output.append(tmp)
                start = idx + 1
        res = content[start:]
        if len(res) > 0:
            output.append(res)
        return output

    def slide_window_chunk(
        self,
        content: Union[str, List[str]],
        chunk_size: int = 2000,
        window_length: int = 300,
        sep: str = "\n",
        prefix: str = "SlideWindow",
    ) -> List[Chunk]:

        if isinstance(content, str):
            content = self.split_sentence(content)
        splitted = []
        cur = []
        cur_len = 0
        for sentence in content:
            if cur_len + len(sentence) > chunk_size:
                splitted.append(cur)
                tmp = []
                cur_len = 0
                for item in cur[::-1]:
                    if cur_len >= window_length:
                        break
                    tmp.append(item)
                    cur_len += len(item)
                cur = tmp[::-1]

            cur.append(sentence)
            cur_len += len(sentence)
        if len(cur) > 0:
            splitted.append(cur)

        output = []
        for idx, sentences in enumerate(splitted):
            chunk_name = f"{prefix}#{idx}"
            chunk = Chunk(
                id=Chunk.generate_hash_id(chunk_name),
                name=chunk_name,
                content=sep.join(sentences),
            )
            output.append(chunk)
        return output

    def chunk_split(
        self,
        chunk: Chunk,
    ) -> List[Chunk]:
        text = chunk.content

        pattern = re.compile(self.pattern, re.DOTALL)

        # 查找所有匹配项
        matches = pattern.finditer(text)

        # 遍历所有匹配项
        chunks = []
        for match in matches:
            chunk = Chunk(
                chunk_header=match.group(self.group["header"]),
                name=match.group(self.group["name"]),
                id=Chunk.generate_hash_id(match.group(self.group["content"])),
                content=match.group(self.group["content"]),
            )
            chunk = [chunk]

            if self.chunk_cut_num:
                chunk = self.slide_window_chunk(
                    content=chunk[0].content,
                    chunk_size=self.chunk_cut_num,
                    window_length=self.chunk_cut_num / 4,
                    sep="\n",
                    prefix=chunk[0].name,
                )

            chunks.extend(chunk)

        return chunks

    def invoke(self, input: Chunk, **kwargs) -> List[Output]:

        chunks = self.chunk_split(input)
        return chunks

    def to_rest(self):
        pass

    @classmethod
    def from_rest(cls, rest_model):
        pass


class LayeredPatternSpliter(PatternSplitter):
    pass


def _test():
    pattern_dict = {
        "pattern": r"(\d+)\.([^0-9]+?)？([^0-9第版].*?)(?=\d+\.|$)",
        "group": {"header": 2, "name": 2, "content": 0},
    }
    ds = PatternSplitter(pattern_dict=pattern_dict)
    from kag.builder.component.reader.pdf_reader import PDFReader

    reader = PDFReader()
    file_path = os.path.dirname(__file__)
    test_file_path = os.path.join(file_path, "../../../../tests/builder/data/aiwen.pdf")
    pre_output = reader._handle(test_file_path)

    handle_input = pre_output[0]
    handle_result = ds._handle(handle_input)
    print("handle_result", handle_result)

    return handle_result


if __name__ == "__main__":
    res = _test()
    print(res)
