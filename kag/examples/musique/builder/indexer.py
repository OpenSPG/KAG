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
from kag.common.registry import Registrable, import_modules_from_path
from kag.builder.component import KGWriter
from kag.interface import ExtractorABC, SplitterABC, VectorizerABC, SourceReaderABC
from knext.builder.builder_chain_abc import BuilderChainABC

logger = logging.getLogger(__name__)
import_modules_from_path(".")


class MusiqueBuilderChain(BuilderChainABC, Registrable):
    def __init__(
        self,
        reader: SourceReaderABC,
        splitter: SplitterABC,
        extractor: ExtractorABC,
        vectorizer: VectorizerABC,
        writer: KGWriter,
    ):
        self.reader = reader
        self.splitter = splitter
        self.extractor = extractor
        self.vectorizer = vectorizer
        self.writer = writer

    def build(self, **kwargs):
        return (
            self.reader
            >> self.splitter
            >> self.extractor
            >> self.vectorizer
            >> self.writer
        )


def buildKB(file_path):
    from kag.common.conf import KAG_CONFIG

    chain_config = KAG_CONFIG.all_config["chain"]
    chain = MusiqueBuilderChain.from_config(chain_config)
    chain.invoke(file_path=file_path, max_workers=20)

    logger.info(f"\n\nbuildKB successfully for {corpusFilePath}\n\n")


if __name__ == "__main__":
    file_path = "./data/musique_sub_corpus.json"
    # filePath = "./data/musique_train_corpus.json"

    buildKB(file_path)
