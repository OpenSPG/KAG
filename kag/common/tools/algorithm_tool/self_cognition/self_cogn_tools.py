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

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.config import get_default_chat_llm_config
from kag.interface import LLMClient, PromptABC, ToolABC
from kag.solver.utils import init_prompt_with_fallback


@ToolABC.register("self_cognition")
class SelfCognExecutor(ToolABC):
    def __init__(
        self,
        llm_module: LLMClient = None,
        self_cognition_prompt: PromptABC = None,
        **kwargs,
    ):
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        self.llm_module = llm_module or LLMClient.from_config(
            get_default_chat_llm_config()
        )
        self.self_cognition_prompt = self_cognition_prompt or init_prompt_with_fallback(
            "self_cognition", self.kag_project_config.biz_scene
        )

        self.docs_zh = [
            "我是基于蚂蚁集团开源的专业领域知识服务框架KAG搭建的问答助手，我擅长逻辑推理、数值计算等任务，可以协助你解答相关问题、提供信息支持或进行数据分析。如果有具体需求，随时告诉我",
        ]
        doc_path_zh = f"{os.path.join(os.path.abspath(os.path.dirname(__file__)), './docs/kag_intro_zh.md')}"
        with open(doc_path_zh, "r") as f:
            text = f.read()
            self.docs_zh.append(text)

        self.docs_en = [
            "I am based on the open-source professional domain knowledge service framework KAG by Ant Group. I specialize in tasks such as logical reasoning and numerical calculations. I can assist you in answering related questions, providing information support, or performing data analysis. If you have specific needs, feel free to let me know."
        ]
        doc_path_en = f"{os.path.join(os.path.abspath(os.path.dirname(__file__)), './docs/kag_intro_en.md')}"
        with open(doc_path_en, "r") as f:
            text = f.read()
            self.docs_en.append(text)

    @property
    def category(self):
        return "SelfCognition"

    def invoke(self, query: str, **kwargs):
        return self.llm_module.invoke(
            {"question": query}, self.self_cognition_prompt, with_json_parse=False
        )

    def get_docs(self):
        if self.kag_project_config.language == "zh":
            return self.docs_zh
        else:
            return self.docs_en

    def schema(self):
        return {
            "name": "SelfCognition",
            "description": "Performs query-to-query operations and is solely used to indicate that the task has been completed.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }
