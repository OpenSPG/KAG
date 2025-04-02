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
from kag.common.registry import import_modules_from_path

from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)

def AtomicQuestionKBInjection(file_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_pike_kb_injection_pipeline"]
    )
    runner.invoke(file_path)

    logger.info(f"\n\nDecomposer atomic question successfully for {file_path}\n\n")


def AtomicQuestionChunkInjection(file_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_pike_chunk_injection_pipeline"]
    )
    runner.invoke(file_path)

    logger.info(f"\n\nDecomposer atomic question successfully for {file_path}\n\n")


if __name__ == "__main__":
    import_modules_from_path(".")
    file_path = "/Users/laven/Desktop/常识知识图谱/源代码/Semantic_KAG/KAG/dep/KAG/kag/examples/musique_pike/builder/data/musique_corpus.json"

    # AtomicQuestionChunkInjection(file_path)
    AtomicQuestionKBInjection(file_path)