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

import re
import json
import logging
import os
from typing import Type, List


from kag.interface.builder import ExtractorABC
from kag.common.base.prompt_op import PromptOp
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


class TableClassify(ExtractorABC):
    """
    table classify
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        self.prompt_config = self.config.get("prompt", {})
        self.biz_scene = self.prompt_config.get("biz_scene") or os.getenv(
            "KAG_PROMPT_BIZ_SCENE", "default"
        )
        self.language = self.prompt_config.get("language") or os.getenv(
            "KAG_PROMPT_LANGUAGE", "zh"
        )
        self.table_context = PromptOp.load("table", "table_context")(
            language=self.language, project_id=self.project_id
        )
        self.classify_prompt = PromptOp.load("table", "table_classify")(
            language=self.language, project_id=self.project_id
        )

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return Chunk

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        invoke
        """
        try:
            return self.do_invoke(input, **kwargs)
        except Exception:
            logger.exception("error")
            return []

    def do_invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        进行表格分类
        """
        table_chunk: Chunk = input
        if table_chunk.type != ChunkTypeEnum.Table:
            return []

        # 提取全局信息
        table_desc, keywords, table_name = self._get_table_context(
            table_chunk=table_chunk
        )
        table_desc = "\n".join(table_desc)

        _content = table_chunk.content
        classify_input = {"table": _content, "context": table_desc}

        table_type, table_info = self.llm.invoke(
            {
                "input": json.dumps(classify_input, ensure_ascii=False, sort_keys=True),
            },
            self.classify_prompt,
            with_json_parse=True,
            with_except=True,
        )
        table_chunk.kwargs["table_type"] = table_type
        table_chunk.kwargs["table_info"] = table_info
        table_chunk.kwargs["table_name"] = table_name
        table_chunk.kwargs["context"] = table_desc
        table_chunk.kwargs["keywords"] = keywords
        return [table_chunk]

    def _get_table_context(self, table_chunk: Chunk):
        # 提取表格全局关键字
        table_desc = ""
        keywords = []
        table_context_str = self._get_table_context_str(table_chunk=table_chunk)
        _table_context = self.llm.invoke(
            {
                "input": table_context_str,
            },
            self.table_context,
            with_json_parse=True,
            with_except=True,
        )
        table_desc = _table_context["table_desc"]
        keywords = _table_context["keywords"]
        table_name = _table_context["table_name"]
        return table_desc, keywords, table_name

    def _get_table_context_str(self, table_chunk: Chunk):
        if "context" in table_chunk.kwargs:
            table_context_str = table_chunk.name + "\n" + table_chunk.kwargs["context"]
        else:
            table_context_str = table_chunk.name + "\n" + table_chunk.content
        if len(table_context_str) <= 0:
            return None
        return table_context_str