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
import copy
import logging
import os
from typing import Dict, Type, List

from tenacity import stop_after_attempt, retry

from kag.builder.prompt.spg_prompt import SPG_KGPrompt
from kag.interface.builder import ExtractorABC
from kag.common.base.prompt_op import PromptOp
from knext.schema.client import OTHER_TYPE, CHUNK_TYPE, BASIC_TYPES
from kag.common.utils import processing_phrases, to_camel_case
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from knext.schema.client import SchemaClient
from knext.schema.model.base import SpgTypeEnum

logger = logging.getLogger(__name__)


class KAGExtractor(ExtractorABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        from kag.builder.component.table.table_classify import TableClassify
        from kag.builder.component.table.table_extractor import TableExtractor
        from kag.builder.component.extractor.text_extractor import TextExtractor

        self._table_classify = TableClassify(**kwargs)
        self._table_extractor = TableExtractor(**kwargs)
        self._text_extractor = TextExtractor(**kwargs)

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        from kag.builder.model.chunk import ChunkTypeEnum

        # print(f"input = {input}, id = {id(input)}")
        if input.type == ChunkTypeEnum.Text:
            print("Run extract on Text chunk")
            output = self._text_extractor.invoke(input, **kwargs)
        elif input.type == ChunkTypeEnum.Table:
            print("Run extract on Table chunk")
            chunk = self._table_classify.invoke(input, **kwargs)[0]
            output = self._table_extractor.invoke(chunk, **kwargs)[0]
        else:
            print(f"Unknown chunk type: {input.type}")
            output = []

        if not isinstance(output, list):

            output = [output]
        # print(f"KAGExtractor input: {input.type}, output:\n{output}")
        return output
