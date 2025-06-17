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
import logging
from typing import Dict
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import ExecutorABC, LLMClient, Context, PromptABC
from kag.solver.executor.mcp.mcp_client import MCPClient

logger = logging.getLogger()


@ExecutorABC.register("mcp_executor")
class McpExecutor(ExecutorABC):
    def __init__(
        self,
        store_path: str,
        name: str,
        description: str,
        llm: LLMClient,
        prompt: PromptABC = None,
        env: Dict = {},
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.mcp_file_path = self.download_data(store_path)
        self.prompt = prompt
        self.env = dict(env)
        self.llm = llm
        self.mcp_client = MCPClient(self.llm, self.prompt)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config

    def download_data(self, input: str, **kwargs):
        """
        Downloads data from a given input URL or returns the input directly if it is not a URL.

        Args:
            input (Input): The input source, which can be a URL (starting with "http://" or "https://") or a local path.
            **kwargs: Additional keyword arguments (currently unused).

        Returns:
            List[Output]: A list containing the local file path if the input is a URL, or the input itself if it is not a URL.

        """
        if input.startswith("http://") or input.startswith("https://"):
            from kag.common.utils import download_from_http

            local_file_path = os.path.join(
                self.kag_project_config.ckpt_dir, "mcp_service"
            )
            if not os.path.exists(local_file_path):
                os.makedirs(local_file_path)
            from urllib.parse import urlparse

            parsed_url = urlparse(input)
            local_file = os.path.join(
                local_file_path, os.path.basename(parsed_url.path)
            )

            local_file = download_from_http(input, local_file)
            return local_file
        return input

    async def ainvoke(self, query, task, context: Context, **kwargs):
        task_query = task.arguments["query"]
        try:
            await self.mcp_client.connect_to_server(self.mcp_file_path, self.env)
        except Exception as e:
            await self.mcp_client.cleanup()
            logger.error(f"Failed to connect to server: {e}")
        response = await self.mcp_client.process_query(task_query)
        task.update_result(response)
        return response


def schema(self, func_name: str = None) -> dict:
    """Function schema definition for OpenAI Function Calling

    Returns:
        dict: Schema definition in OpenAI Function format
    """
    return {
        "name": self.name,
        "description": self.description,
        "parameters": {
            "query": {
                "type": "string",
                "description": "User-provided query for retrieval.",
                "optional": False,
            },
        },
    }
