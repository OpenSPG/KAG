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


import json
from contextlib import AsyncExitStack
from typing import Optional, Dict


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from kag.interface import LLMClient, PromptABC


class MCPClient:
    def __init__(self, llm: LLMClient, prompt: PromptABC = None):
        """初始化 MCP 客户端"""
        self.llm = llm
        self.prompt = prompt or PromptABC.from_config({"type": "default_mcp_tool_call"})

        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str, env: Dict):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=env
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = self.prompt.build_prompt(query)
        response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                },
            }
            for tool in response.tools
        ]
        stream = self.llm.stream
        self.llm.stream = False
        response = await self.llm.acall(messages=messages, tools=available_tools)
        self.llm.stream = stream
        # process tool call
        if not isinstance(response, str) and response.tool_calls:
            tool_calls_message = response.model_dump()
            messages.append(tool_calls_message)
            for tool_call in response.tool_calls:
                tool_call = tool_call.dict()["function"]
                tool_name = tool_call["name"]
                tool_args = json.loads(tool_call["arguments"])
                result = await self.session.call_tool(tool_name, tool_args)
                if "id" in tool_call:
                    messages.append(
                        {
                            "role": "tool",
                            "content": result.content[0].text,
                            "tool_call_id": tool_call["id"],
                        }
                    )
                else:
                    messages.append(
                        {
                            "role": "tool",
                            "content": result.content[0].text,
                        }
                    )
            final_response = await self.llm.acall(messages=messages)
            return final_response
        else:
            return response
