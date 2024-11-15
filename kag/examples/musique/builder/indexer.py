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
import json
import logging
import os
from typing import List, Type

from kag.builder.component import KGWriter
from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.splitter import LengthSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.model.chunk import Chunk
from knext.builder.builder_chain_abc import BuilderChainABC
from kag.interface.builder import SourceReaderABC
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


class MusiqueCorpusReader(SourceReaderABC):
    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return Chunk

    def get_basename(self, file_name: str):
        base, ext = os.path.splitext(os.path.basename(file_name))
        return base

    def invoke(self, input: str, **kwargs) -> List[Output]:
        id_column = kwargs.get("id_column", "title")
        name_column = kwargs.get("name_column", "title")
        content_column = kwargs.get("content_column", "text")

        if os.path.exists(str(input)):
            with open(input, "r") as f:
                corpusList = json.load(f)
        else:
            corpusList = input
        chunks = []

        for item in corpusList:
            chunk = Chunk(
                id=item[id_column],
                name=item[name_column],
                content=item[content_column],
            )
            chunks.append(chunk)
        return chunks


class MusiqueBuilderChain(BuilderChainABC):
    def build(self, **kwargs):
        source = MusiqueCorpusReader()
        splitter = LengthSplitter(window_length=2000)
        extractor = KAGExtractor()
        vectorizer = BatchVectorizer()
        sink = KGWriter()

        return source >> splitter >> extractor >> vectorizer >> sink


def buildKB(corpusFilePath):
    MusiqueBuilderChain().invoke(file_path=corpusFilePath, max_workers=20)

    logger.info(f"\n\nbuildKB successfully for {corpusFilePath}\n\n")


if __name__ == "__main__":
    filePath = "./data/musique_sub_corpus.json"
    # filePath = "./data/musique_train_corpus.json"

    corpusFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    buildKB(corpusFilePath)
