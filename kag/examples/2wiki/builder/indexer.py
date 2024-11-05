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
from typing import Type, List

from kag.builder.component import KGWriter
from kag.builder.component.extractor import KAGExtractor
from kag.builder.component.splitter import LengthSplitter
from kag.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from kag.builder.model.chunk import Chunk
from kag.interface.builder.reader_abc import SourceReaderABC
from knext.common.base.runnable import Input, Output
from knext.builder.builder_chain_abc import BuilderChainABC

logger = logging.getLogger(__name__)


class TwowikiCorpusReader(SourceReaderABC):
    @property
    def input_types(self) -> Type[Input]:
        """The type of input this Runnable object accepts specified as a type annotation."""
        return str

    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return Chunk

    def invoke(self, input: str, **kwargs) -> List[Output]:
        if os.path.exists(str(input)):
            with open(input, "r") as f:
                corpus = json.load(f)
        else:
            corpus = json.loads(input)
        chunks = []

        for idx, item in enumerate(corpus):
            chunk = Chunk(
                id=str(idx),
                name=item["title"],
                content=item["text"],
            )
            chunks.append(chunk)
        return chunks


class TwowikiBuilderChain(BuilderChainABC):
    def build(self, **kwargs):
        source = TwowikiCorpusReader()
        splitter = LengthSplitter(split_length=2000)
        extractor = KAGExtractor()
        vectorizer = BatchVectorizer()
        sink = KGWriter()

        return source >> splitter >> extractor >> vectorizer >> sink


def buildKB(corpusFilePath):
    TwowikiBuilderChain().invoke(file_path=corpusFilePath, max_workers=20)

    logger.info(f"\n\nbuildKB successfully for {corpusFilePath}\n\n")


if __name__ == "__main__":
    filePath = "./data/2wiki_sub_corpus.json"
    # filePath = "./data/2wiki_corpus.json"
    corpusFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), filePath)
    buildKB(corpusFilePath)
