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
import logging 
import os
import re
from typing import List, Type,Union

from kag.interface.builder import SplitterABC
from kag.builder.prompt.outline_prompt import OutlinePrompt
from kag.builder.model.chunk import Chunk
from knext.common.base.runnable import Input, Output
from kag.common.llm.client.llm_client import LLMClient

logger = logging.getLogger(__name__)

class OutlineSplitter(SplitterABC):
    
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        self.prompt = OutlinePrompt(language)
        
    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk
    
    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]]) -> List[Chunk]:
        if isinstance(chunk, Chunk):
            chunk = [chunk]
        outlines = []
        for c in chunk:
            outline = self.llm.invoke({"input": c.content}, self.prompt)
            outlines.extend(outline)
        content = "\n".join([c.content for c in chunk])
        chunks = self.sep_by_outline(content, outlines)
        return chunks
    
    def sep_by_outline(self,content,outlines):
        position_check = []
        for outline in outlines:
            start = content.find(outline)
            position_check.append((outline,start))
        chunks = []
        for idx,pc in enumerate(position_check):
            chunk = Chunk(
                id = Chunk.generate_hash_id(f"{pc[0]}#{idx}"),
                name=f"{pc[0]}#{idx}",
                content=content[pc[1]:position_check[idx+1][1] if idx+1 < len(position_check) else len(position_check)],
            )
            chunks.append(chunk)
        return chunks
    
    def invoke(self,input: Input, **kwargs) -> List[Chunk]:
        chunks = self.outline_chunk(input)
        return chunks

if __name__ == "__main__":
    from kag.builder.component.splitter.length_splitter import LengthSplitter
    from kag.builder.component.splitter.outline_splitter import OutlineSplitter
    from kag.builder.component.reader.docx_reader import DocxReader
    from kag.common.env import init_kag_config
    init_kag_config(os.path.join(os.path.dirname(__file__),"../../../../tests/builder/component/test_config.cfg"))
    docx_reader = DocxReader()
    length_splitter = LengthSplitter(split_length=8000)
    outline_splitter = OutlineSplitter()
    docx_path = os.path.join(os.path.dirname(__file__),"../../../../tests/builder/data/test_docx.docx")
    # chain = docx_reader >> length_splitter >> outline_splitter
    chunk = docx_reader.invoke(docx_path)
    chunks = length_splitter.invoke(chunk)
    chunks = outline_splitter.invoke(chunks)
    print(chunks)