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

import argparse
import json

from typing import List


class KagMcpServer(object):
    _supported_tools = "qa-pipeline", "kb-retrieve"
    _default_server_name = "kag"
    _default_sse_port = 3000

    @classmethod
    def add_options(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--transport",
            help="specify MCP server transport; default to sse",
            type=str,
            default="sse",
            choices=("sse", "stdio"),
        )
        parser.add_argument(
            "-p",
            "--port",
            help="specify sse server port; default to %d" % cls._default_sse_port,
            type=int,
            default=cls._default_sse_port,
        )
        all_supported_tools = ",".join(cls._supported_tools)
        parser.add_argument(
            "--enabled-tools",
            help="specify enabled tools, a comma separated list; "
            "default to qa-pipeline; "
            "use 'all' for all the supported tools: %s" % all_supported_tools,
            type=str,
            default="qa-pipeline",
        )

    @classmethod
    def run(cls, args: argparse.Namespace) -> None:
        transport = args.transport
        port = args.port
        enabled_tools = args.enabled_tools
        server = cls(transport=transport, port=port, enabled_tools=enabled_tools)
        server.serve()

    def __init__(self, transport: str, port: int, enabled_tools: str) -> None:
        self._transport = transport
        self._port = port
        self._enabled_tools = tuple(self._get_enabled_tools(enabled_tools))
        self._check_mcp_package()
        self._create_mcp_server()

    @classmethod
    def _get_enabled_tools(cls, spec: str) -> List[str]:
        if spec == "all":
            return list(cls._supported_tools)
        tools = []
        names = spec.split(",")
        for name in names:
            if name in cls._supported_tools:
                tools.append(name)
            else:
                message = "unknown tool %s" % name
                raise RuntimeError(message)
        return tools

    @classmethod
    def _check_mcp_package(cls):
        import importlib.util

        if importlib.util.find_spec("mcp") is None:
            message = "Please install 'mcp' to use KAG MCP server: `python -m pip install mcp`"
            raise ModuleNotFoundError(message)

    def _create_mcp_server(self) -> None:
        from mcp.server.fastmcp import FastMCP  # noqa

        if self._transport == "sse":
            mcp_server = FastMCP(self._default_server_name, port=self._port)
        else:
            mcp_server = FastMCP(self._default_server_name)
        self._mcp_server = mcp_server
        self._add_mcp_tools()

    def _add_mcp_tools(self) -> None:
        for name in self._enabled_tools:
            if name == "qa-pipeline":
                self._add_qa_pipeline_tool()
            elif name == "kb-retrieve":
                self._add_kb_retrieve_tool()
            else:
                assert False

    def _add_qa_pipeline_tool(self) -> None:
        async def qa_pipeline(query: str) -> str:
            """
            Query the knowledge-base with `query`.

            Args:
                query: question to ask
            """

            from kag.open_benchmark.utils.eval_qa import EvalQa

            qa_obj = EvalQa(task_name="qa", solver_pipeline_name="kag_solver_pipeline")
            answer, trace = await qa_obj.qa(query=query, gold="")
            return answer

        self._mcp_server.add_tool(qa_pipeline)

    def _add_kb_retrieve_tool(self) -> None:
        async def kb_retrieve(query: str) -> str:
            """
            Query the knowledge-base with `query` to retrieve SPO-triples and document chunks.

            Args:
                query: query to execute
            """
            from kag.common.conf import KAG_CONFIG
            from kag.interface import ExecutorABC
            from kag.interface import Task
            from kag.interface import Context

            executor = ExecutorABC.from_config(
                KAG_CONFIG.all_config["kag_hybrid_executor"]
            )
            executor_schema = executor.schema()
            executor_name = executor_schema["name"]
            executor_arguments = {
                "query": query,
            }
            task = Task(executor=executor_name, arguments=executor_arguments)
            context = Context()
            await executor.ainvoke(query=query, task=task, context=context)
            data = {
                "summary": task.result.summary,
                "references": task.result.to_dict(),
            }
            result = json.dumps(
                data, separators=(",", ": "), indent=4, ensure_ascii=False
            )
            return result

        self._mcp_server.add_tool(kb_retrieve)

    def serve(self) -> None:
        if self._transport == "sse":
            self._mcp_server.run(transport="sse")
        elif self._transport == "stdio":
            self._mcp_server.run(transport="stdio")
        else:
            assert False
