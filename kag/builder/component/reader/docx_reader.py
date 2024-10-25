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
from typing import List, Type,Union

from docx import Document

from kag.builder.component.reader import MarkDownReader
from kag.builder.model.chunk import Chunk
from kag.interface.builder import SourceReaderABC
from knext.common.base.runnable import Input, Output

from kag.common.llm.client import LLMClient
from kag.builder.prompt.outline_prompt import OutlinePrompt

def split_txt(content):
    from modelscope.outputs import OutputKeys
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    p = pipeline(
        task=Tasks.document_segmentation,
        model='damo/nlp_bert_document-segmentation_chinese-base')

    result = p(documents=content)
    result = result[OutputKeys.TEXT]
    
    res = [r for r in result.split('\n\t') if len(r) > 0]
    
    return res


    
class DocxReader(SourceReaderABC):
    """
    A class for reading Docx files, inheriting from SourceReader.
    This class is specifically designed to extract text content from Docx files and generate Chunk objects based on the extracted content.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.split_level = kwargs.get("split_level", 3)
        self.split_using_outline = kwargs.get("split_using_outline", True)
        self.outline_flag = True
        self.llm = self._init_llm()
        language = os.getenv("KAG_PROMPT_LANGUAGE", "zh")
        self.prompt = OutlinePrompt(language)

    @property
    def input_types(self) -> Type[Input]:
        return str

    @property
    def output_types(self) -> Type[Output]:
        return Chunk
    
    def outline_chunk(self, chunk: Union[Chunk, List[Chunk]],basename) -> List[Chunk]:
        if isinstance(chunk, Chunk):
            chunk = [chunk]
        outlines = []
        for c in chunk:
            outline = self.llm.invoke({"input": c.content}, self.prompt)
            outlines.extend(outline)
        content = "\n".join([c.content for c in chunk])
        chunks = self.sep_by_outline(content, outlines,basename)
        return chunks
    
    def sep_by_outline(self,content,outlines,basename):
        position_check = []
        for outline in outlines:
            start = content.find(outline)
            position_check.append((outline,start))
        chunks = []
        for idx,pc in enumerate(position_check):
            chunk = Chunk(
                id = Chunk.generate_hash_id(f"{basename}#{pc[0]}"),
                name=f"{basename}#{pc[0]}",
                content=content[pc[1]:position_check[idx+1][1] if idx+1 < len(position_check) else len(position_check)],
            )
            chunks.append(chunk)
        return chunks

    @staticmethod
    def _extract_text_from_docx(doc: Document) -> str:
        """
        Extracts text from a Docx document.

        This method iterates through all paragraphs in the provided Docx document,
        appending each paragraph's text to a list, and then joins these texts into
        a single string separated by newline characters, effectively extracting the
        entire text content of the document.

        Args:
            doc (Document): A Document object representing the Docx file from which
                            text is to be extracted.

        Returns:
            str: A string containing all the text from the Docx document, with paragraphs
                 separated by newline characters.
        """
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return full_text
    
    def _get_title_from_text(self, text: str) -> str:
        text = text.strip()
        title = text.split('\n')[0]
        text = "\n".join(text.split('\n'))
        return title,text

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Processes the input Docx file, extracts its text content, and generates a Chunk object.

        Args:
            input (Input): The file path of the Docx file to be processed.
            **kwargs: Additional keyword arguments, not used in the current implementation.

        Returns:
            List[Output]: A list containing a single Chunk object with the extracted text.

        Raises:
            ValueError: If the input is empty.
            IOError: If the file cannot be read or the text extraction fails.
        """

        if not input:
            raise ValueError("Input cannot be empty")
        
        chunks = []
        
        try:
            doc = Document(input)
            full_text = self._extract_text_from_docx(doc)
            content = "\n".join(full_text)
        except OSError as e:
            raise IOError(f"Failed to read file: {input}") from e

        basename, _ = os.path.splitext(os.path.basename(input))

        for text in full_text:
            title,text = self._get_title_from_text(text)
            chunk = Chunk(
                id=Chunk.generate_hash_id(f"{basename}#{title}"),
                name=f"{basename}#{title}",
                content=text,
            )
            chunks.append(chunk)

        if len(chunks) < 2:
            chunks = self.outline_chunk(chunks,basename)
        
        if len(chunks) < 2:
            semantic_res = split_txt(content)
            chunks = [Chunk(
                id=Chunk.generate_hash_id(input+"#"+r[:10]),
                name=basename+"#"+r[:10],
                content=r,
            ) for r in semantic_res]

        return chunks


if __name__== "__main__":
    reader = DocxReader()
    print(reader.output_types)
    file_path = os.path.dirname(__file__)
    res = reader.invoke(os.path.join(file_path,"../../../../tests/builder/data/test_docx.docx"))
    print(res)