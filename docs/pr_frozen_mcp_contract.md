# PR Description — `feat/mcp-frozen-contract`

> Branch: `feat/mcp-frozen-contract` · Base: upstream default branch
> Commits: `ca69a671` · `69d3a7a0` · `156ed685` · `0ec71b49`

---

## English

### Title

**feat(mcp): align `kag mcp-server` with the frozen OPENKG WebUI tool contracts**

### Background / Motivation

OPENKG WebUI (the `kagweb` repository) integrates with KAG through an MCP tool surface and has defined and **frozen** four tool contracts (`kag_solve` / `kag_schema` / `kag_reason` / `kag_status` — inputSchema and return schema frozen since v1). Until now these contracts only existed in the standalone `kag-bridge` (FastMCP, dual transport: stdio + streamable-http).

This PR aligns the **same frozen contracts into the upstream `kag mcp-server`**, making KAG's built-in MCP server a second host (dual-hosting). OPENKG WebUI stays unchanged when switching hosts.

### Changes

`kag/mcp/server/kag_mcp_server.py`:

1. **`kag-solve`** (`ca69a671`) — align the frozen `kag_solve` contract:
   - Reuses the upstream `OpenSPGReporter` in-memory product (`host_addr=None`, zero network) through `do_qa_pipeline`, returning the frozen `{answer, reference, subgraph, cost_ms, namespace}`.
   - Fixes an upstream singleton trap: `KAGConfigMgr.all_config` caches on first access, and the module-top-level import chain initializes it with an empty config in a config-less cwd; `_load_kag_config` now calls `KAG_CONFIG.initialize(config_file=...)` to reset explicitly.
2. **`kag-status`** (`ca69a671`) — config / project / LLM connectivity probe; structured errors; no credential echo.
3. **`kag-schema`** (`156ed685`) — `ReasonerClient.get_reason_schema` → `{project_id, namespace, spg_types}` (keys are namespace-qualified full names).
4. **`kag-reason`** (`156ed685`) — direct `POST /public/v1/reason/run` (in a thread pool):
   - Why: the `ReasonTask` client model does not map `resultMessage` (error details exist only in the raw response); the direct call keeps the frozen error detail.
   - `params` values are JSON-stringified (raw arrays from an agent also work); rows capped at 200 with a `truncated` flag; errors clipped to 600 chars.
5. **Concurrency safety** (`69d3a7a0` / `0ec71b49`, review fixes) — `KAGConfigAccessor` / `KAG_CONFIG` are process-global singletons and `initialize()` rewrites the singleton; all four tools now load config under a module-level `_solve_semaphore` (`asyncio.Semaphore(1)`) so every global initialization is mutually exclusive.

### Frozen contracts (v1, identical to the standalone kag-bridge)

| Tool | Input | Return highlights |
|---|---|---|
| `kag_solve` | `question`, `use_pipeline` | `{answer, reference[], subgraph{...}, cost_ms, namespace}` |
| `kag_schema` | — | `{project_id, namespace, spg_types{fullName: {spg_type_enum}}}` |
| `kag_reason` | `dsl`, `params` | `{status, header, rows(≤200), row_count, truncated, cost_ms, namespace, error?}` |
| `kag_status` | — | `{bridge, project, namespace, llm_configured}` (structured errors, no credentials) |

### Verification (local stdio against a live OpenSPG)

- `kag_status` → `{bridge: ok, project: 3, namespace: m0ProbeLive, llm_configured: true}`
- `kag_schema` → 19 SPG types (`m0ProbeLive.Person` present)
- `kag_reason` → `workFor` query FINISH, 3 rows (Zhang San → Kaiyuan University)
- `kag_solve` → same `do_qa_pipeline` path already E2E-verified in M3
- Regression: all four tools still work after the concurrency-semaphore fix

### Known boundaries (need upstream confirmation)

- **CLI subcommand smoke fails**: `python -m kag.bin.kag_cmds mcp-server --transport stdio --enabled-tools ...` shows `Connection closed` in this environment while direct `KagMcpServer(...).serve()` works — likely stdout pollution from the import chain or arg wiring; this looks like a CLI-wrapper issue, worth verifying upstream.
- **Tests not wired into KAG CI yet**: the contract-verification scripts live on the OPENKG WebUI side (`kagweb/tests/`); the contract test seeds can be moved here if approved.
- Tool surface keeps the existing `enabled-tools` allowlist mechanism; the transport layer is untouched.

### Review focus

1. Side effects of the explicit `KAG_CONFIG.initialize()` reset in `_load_kag_config`.
2. Throughput impact of the serialization semaphore (acceptable for this repo's current mcp-server usage).
3. Root cause of the CLI subcommand `Connection closed`.

---

## 中文

### 标题

**feat(mcp)：将 `kag mcp-server` 对齐 OPENKG WebUI 冻结工具契约**

### 背景 / 动机

OPENKG WebUI（`kagweb` 仓库）通过 MCP 工具面与 KAG 集成，已定义并**冻结**了 4 个工具契约（`kag_solve` / `kag_schema` / `kag_reason` / `kag_status`，inputSchema 与返回 schema 自 v1 冻结）。此前这些契约仅存在于独立部署的 `kag-bridge`（FastMCP，stdio + streamable-http 双 transport）。

本 PR 将同一组冻结契约**对齐进上游 `kag mcp-server`**，使 KAG 自带 MCP server 成为第二宿主（双宿主）；切换宿主时 OPENKG WebUI 侧零改动。

### 变更内容

`kag/mcp/server/kag_mcp_server.py`：

1. **`kag-solve`**（`ca69a671`）——对齐 `kag_solve` 冻结契约：
   - 复用上游 `OpenSPGReporter` 纯内存产物（`host_addr=None`，零网络），经 `do_qa_pipeline` 返回冻结的 `{answer, reference, subgraph, cost_ms, namespace}`
   - 修复上游单例陷阱：`KAGConfigMgr.all_config` 首调即缓存，模块顶层 import 链会在无配置 cwd 抢先初始化；`_load_kag_config` 改用 `KAG_CONFIG.initialize(config_file=...)` 显式重置
2. **`kag-status`**（`ca69a671`）——配置 / 项目 / LLM 连通性健康探测，结构化错误，不回显凭据
3. **`kag-schema`**（`156ed685`）——`ReasonerClient.get_reason_schema` → `{project_id, namespace, spg_types}`（key 为 namespace 全名）
4. **`kag-reason`**（`156ed685`）——直调 `POST /public/v1/reason/run`（线程池）：
   - 原因：`ReasonTask` 客户端模型不映射 `resultMessage`（错误详情只在原始响应），直调保留冻结的错误详情
   - params 值 JSON 字符串化（agent 传真数组亦可用）；rows ≤200 截断 + `truncated` 标记；错误截 600 字符
5. **并发安全**（`69d3a7a0` / `0ec71b49`，评审修复）——`KAGConfigAccessor` / `KAG_CONFIG` 是进程级全局单例，`initialize()` 会重写该单例；四个工具的所有 config 加载统一纳入模块级 `_solve_semaphore`（`asyncio.Semaphore(1)`），令全局初始化互斥

### 冻结契约（v1，与独立 kag-bridge 完全一致）

| 工具 | 入参 | 返回要点 |
|---|---|---|
| `kag_solve` | `question`, `use_pipeline` | `{answer, reference[], subgraph{...}, cost_ms, namespace}` |
| `kag_schema` | — | `{project_id, namespace, spg_types{全名: {spg_type_enum}}}` |
| `kag_reason` | `dsl`, `params` | `{status, header, rows(≤200), row_count, truncated, cost_ms, namespace, error?}` |
| `kag_status` | — | `{bridge, project, namespace, llm_configured}`（结构化错误，无凭据） |

### 验证（本地 stdio 实测，连真实 OpenSPG）

- `kag_status` → `{bridge: ok, project: 3, namespace: m0ProbeLive, llm_configured: true}`
- `kag_schema` → 19 个 SPG 类型（`m0ProbeLive.Person` 在列）
- `kag_reason` → `workFor` 查询 FINISH 3 rows（张三→开元大学）
- `kag_solve` → 复用 M3 已实测的同一 `do_qa_pipeline` 路径
- 回归：并发信号量修复后四工具仍正常

### 已知边界（需上游确认）

- **CLI 子命令入口冒烟失败**：`python -m kag.bin.kag_cmds mcp-server --transport stdio --enabled-tools ...` 在本环境冒烟出 `Connection closed`（直接 `KagMcpServer(...).serve()` 正常）——疑似 import 链 stdout 污染或参数接线，属 CLI 包装层问题，建议上游核验该入口
- **测试未纳入 KAG CI**：本分支的契约验证脚本在 OPENKG WebUI 侧（`kagweb/tests/`）；如认可，可将契约测试种子迁入本仓库
- 工具面沿用既有 `enabled-tools` 白名单机制，未改 transport 层

### 请 reviewer 关注

1. `_load_kag_config` 的 `KAG_CONFIG.initialize()` 显式重置是否有副作用
2. 信号量序列化对吞吐的影响（本仓库 mcp server 当前场景可接受）
3. CLI 子命令入口的 Connection closed 根因
