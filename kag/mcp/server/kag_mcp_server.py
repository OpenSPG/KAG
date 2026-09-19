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
import asyncio
import json
import os
import time

from typing import List

from kag.solver.reporter.open_spg_reporter import OpenSPGReporter


class KagMcpServer(object):
    # ``kag-solve``/``kag-status`` 为冻结契约(M5-B, docs §A.1) → 与独立
    # kag-bridge 双宿主、KAGWeb 零改动；kag-schema/kag-reason 同风格后续扩展。
    _supported_tools = (
        "qa-pipeline",
        "kb-retrieve",
        "kag-solve",
        "kag-schema",
        "kag-reason",
        "kag-status",
    )
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
            elif name == "kag-solve":
                self._add_kag_solve_tool()
            elif name == "kag-schema":
                self._add_kag_schema_tool()
            elif name == "kag-reason":
                self._add_kag_reason_tool()
            elif name == "kag-status":
                self._add_kag_status_tool()
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

    def _add_kag_solve_tool(self) -> None:
        """冻结契约 kag-solve：LLM 增强推理，返回 {answer, reference, subgraph,
        cost_ms, namespace}——与独立 kag-bridge 同契约（M5-B 双宿主）。"""

        async def kag_solve(question: str, use_pipeline: str = "think_pipeline") -> str:
            """
            LLM-augmented reasoning over the bound KAG project.

            Args:
                question: the question (include any needed conversation context;
                    this tool is stateless single-turn).
                use_pipeline: solver pipeline name; defaults to think_pipeline.
            """
            async with _solve_semaphore:
                cfg = _load_kag_config()
                info = _project_info(cfg)
                task_id = "mcp_%d" % int(time.time() * 1000)
                reporter = _MemoryReporter(
                    task_id=task_id, host_addr=None, project_id=info["project_id"]
                )
                t0 = time.time()
                try:
                    from kag.solver.main_solver import do_qa_pipeline

                    answer = await do_qa_pipeline(
                        use_pipeline,
                        question,
                        cfg,
                        reporter,
                        task_id=task_id,
                        kb_project_ids=[],
                    )
                finally:
                    await reporter.stop()
            stream_data = {}
            try:
                content, _status, _metrics = reporter.generate_report_data()
                stream_data = content.to_dict()
            except Exception:
                pass
            return json.dumps(
                {
                    "answer": str(answer),
                    "reference": stream_data.get("reference", []),
                    "subgraph": stream_data.get("subgraph", []),
                    "cost_ms": int((time.time() - t0) * 1000),
                    "namespace": info["namespace"],
                },
                ensure_ascii=False,
                default=str,
            )

        self._mcp_server.add_tool(kag_solve)

    def _add_kag_schema_tool(self) -> None:
        """冻结契约 kag-schema：SPG 类型清单（只读）。"""

        async def kag_schema() -> str:
            """Read-only summary of the project's SPG types (for reason-DSL tooling)."""
            async with _solve_semaphore:
                cfg = _load_kag_config()
                info = _project_info(cfg)
            try:
                from knext.reasoner.client import ReasonerClient

                rc = ReasonerClient(
                    host_addr=info["host_addr"], project_id=int(info["project_id"])
                )
                spg = rc.get_reason_schema()
            except Exception as exc:  # noqa: BLE001 - 工具结果需结构化错误
                return json.dumps(
                    {"error": "%s: %s" % (type(exc).__name__, exc)}, ensure_ascii=False
                )
            return json.dumps(
                {
                    "project_id": info["project_id"],
                    "namespace": info["namespace"],
                    "spg_types": {
                        name: {"spg_type_enum": str(getattr(v, "spg_type_enum", ""))}
                        for name, v in spg.items()
                    },
                },
                ensure_ascii=False,
                default=str,
            )

        self._mcp_server.add_tool(kag_schema)

    def _add_kag_reason_tool(self) -> None:
        """冻结契约 kag-reason：reason DSL 图查询（只读），返回表格结果。"""

        async def kag_reason(dsl: str, params: dict = None) -> str:
            """
            Run a read-only reason DSL graph query over the bound project.

            Args:
                dsl: reason DSL (MATCH ... RETURN ...). Node types must use the
                    namespace-qualified full name (e.g. m0ProbeLive.Person); relation
                    labels are bare (e.g. workFor); no LIMIT clause is supported.
                params: placeholder substitution; values are stringified (raw arrays
                    are accepted and JSON-serialized).
            """
            import urllib.request

            async with _solve_semaphore:
                cfg = _load_kag_config()
                info = _project_info(cfg)
            normalized = {}
            for key, value in (params or {}).items():
                if isinstance(value, str):
                    normalized[str(key)] = value
                else:
                    normalized[str(key)] = json.dumps(
                        value, ensure_ascii=False, default=str
                    )
            url = "%s/public/v1/reason/run" % info["host_addr"].rstrip("/")
            body = json.dumps(
                {"projectId": int(info["project_id"]), "dsl": dsl, "params": normalized}
            ).encode()
            t0 = time.time()

            def _run():
                req = urllib.request.Request(
                    url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=125) as resp:
                    return json.loads(resp.read())

            try:
                # 同步阻塞（HTTP 往返 + 服务端同步推理）——放线程池避免卡死事件循环
                resp_json = await asyncio.wait_for(asyncio.to_thread(_run), timeout=125)
            except asyncio.TimeoutError:
                return json.dumps({"error": "reason 超时（>125s）"}, ensure_ascii=False)
            except Exception as exc:  # noqa: BLE001
                return json.dumps(
                    {"error": "%s: %s" % (type(exc).__name__, exc)},
                    ensure_ascii=False,
                    default=str,
                )
            task = (resp_json or {}).get("task") or {}
            status = str(task.get("status") or "")
            table = task.get("resultTableResult") or {}
            rows = list(table.get("rows") or [])
            out = {
                "status": status or "UNKNOWN",
                "header": list(table.get("header") or []),
                "rows": rows[:200],
                "row_count": int(table.get("total") or len(rows)),
                "truncated": len(rows) > 200,
                "cost_ms": int((time.time() - t0) * 1000),
                "namespace": info["namespace"],
            }
            if status != "FINISH":
                detail = str(
                    task.get("resultMessage")
                    or ("task not finished: %s" % (status or "UNKNOWN"))
                )
                if len(detail) > 600:
                    detail = detail[:600].rstrip() + "..."
                out["error"] = detail
            return json.dumps(out, ensure_ascii=False, default=str)

        self._mcp_server.add_tool(kag_reason)

    def _add_kag_status_tool(self) -> None:
        """冻结契约 kag-status：bridge/项目配置连通性（回显不含凭据）。"""

        async def kag_status() -> str:
            """Bridge and bound-project configuration health check."""
            try:
                async with _solve_semaphore:
                    cfg = _load_kag_config()
            except Exception as exc:  # noqa: BLE001 - 健康探测需把失败转为状态
                return json.dumps(
                    {"bridge": "error", "error": repr(exc)[:200]}, ensure_ascii=False
                )
            info = _project_info(cfg)
            return json.dumps(
                {
                    "bridge": "ok",
                    "project_id": info["project_id"],
                    "namespace": info["namespace"],
                    "llm_configured": bool(cfg.get("llm")),
                },
                ensure_ascii=False,
            )

        self._mcp_server.add_tool(kag_status)

    def serve(self) -> None:
        if self._transport == "sse":
            self._mcp_server.run(transport="sse")
        elif self._transport == "stdio":
            self._mcp_server.run(transport="stdio")
        else:
            assert False


# —— M5-B 冻结契约 helper：项目配置加载 + memory reporter（host_addr=None 纯内存，
#    M3.0 结论 3）——


class _MemoryReporter(OpenSPGReporter):
    """纯内存 reporter：open_spg_reporter 在 host_addr=None 时零网络，
    do_report 仅需空实现（终态产物经 generate_report_data 组装）。"""

    def do_report(self) -> None:
        pass


def _load_kag_config():
    """读取 KAG_PROJECT_DIR/kag_config.yaml（唯一配置源）。

    ``KAG_CONFIG`` 是进程级单例，首个 get_config() 若在无配置的 cwd 调用会缓存
    空 config——用 ``initialize(config_file=...)`` 显式重置，纳入当前项目配置
    后再取 all_config（M5-B 实测发现的单例污染，见 kag/common/conf.py）。注意
    不得在加载后运行时改 KAG_PROJECT_CONF.host_addr（会丢 llm 键，M0-1 陷阱）。
    """
    proj = os.environ.get("KAG_PROJECT_DIR", "").strip()
    if not proj or not os.path.isfile(os.path.join(proj, "kag_config.yaml")):
        raise RuntimeError("KAG_PROJECT_DIR 未设置或其下无 kag_config.yaml")
    os.chdir(proj)
    from kag.common.conf import KAG_CONFIG

    KAG_CONFIG.initialize(prod=False, config_file=os.path.join(proj, "kag_config.yaml"))
    cfg = KAG_CONFIG.all_config
    if not cfg or "llm" not in cfg or "project" not in cfg:
        raise RuntimeError("kag_config.yaml 缺少 llm / project 配置")
    return cfg


def _project_info(cfg):
    p = cfg.get("project", {}) or {}
    return {
        "namespace": str(p.get("namespace", "")),
        "project_id": str(p.get("id", "")),
        "host_addr": str(p.get("host_addr", "")),
    }


# KAGConfigAccessor/KAG_CONFIG 为进程级全局状态，solve 并发需排队（对齐独立
# kag-bridge 的 §5.1 R3；评审 M9）。
_solve_semaphore = asyncio.Semaphore(1)
