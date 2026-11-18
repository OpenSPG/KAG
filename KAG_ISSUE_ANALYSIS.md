# OpenSPG/KAG GitHub Issue 源码分析与解决方案

> 分析对象：本地 KAG v0.8.0 源码（`/Users/simon/project/KAG`，HEAD=`fdab15b3`）+ OpenSPG/openspg 服务端 Java 源码（`master`）。
> 范围：从 81 个 open issue 中筛选出**可通过源码定位根因**的代码缺陷，逐一给出根因定位、涉及文件与修复方案。
> 结论可信度标注：`[已定位]`（本地 Python 源码逐行验证）、`[服务端]`(openspg Java 源码验证)、`[推测]`（需服务端代码进一步确认）。

---

## 0. Issue 筛选结论

从 81 个 open issue 中，可定位根因的代码 Bug 主要为以下 8 组（含 2 组共享同一根因，`#718`/`#747` 同类）：

| Issue | 标题（简短） | 归属 | 根因置信度 |
|---|---|---|---|
| #685 | table retriever `KeyError: 'beforeText'` | KAG Python | 已定位 |
| #718 | 混合索引/表格索引向量化失败 | KAG Python + 服务端桥接 | 已定位 |
| #747 | `TypeError: 'NoneType' object is not iterable` | KAG Python（与#718同根因） | 已定位 |
| #704 | NER 中文 Schema 拼接 | KAG Python | 已定位 |
| #721 | `McpExecutor` 缺 `kag_project_config` | KAG Python（已修复） | 已定位 |
| #732 | eval 检索/读取服务端 NPE | openspg Java | 已定位 |
| #720 | solver 复现 HotpotQA 图数据为空 / 分数低 | KAG 数据流 + 配置 | 已定位(数据流) |
| #737 | 实体 id/name 标点被过滤 | openspg 服务端 | 推测 |

其余 issue 多为：纯提问/维护性（#752 #740 #738 #687 #684 #692…）、文档改进（#751 #750 #726 #698…）、非代码问题的使用咨询（#690 #688 #703 #695…），不在本次代码 Bug 分析范围。

---

## 1. #685 — `table_retriever.py` `KeyError: 'beforeText'`

**状态**：`[已定位]` KAG Python

**根因：key 命名规范不一致（camelCase vs snake_case）。**

- 构建侧把表的前缀/后缀写入属性名时用的是 **snake_case**：
  - [kag/builder/component/extractor/table_extractor.py](file:///Users/simon/project/KAG/kag/builder/component/extractor/table_extractor.py#L114) `"before_text": before_text`
  - [kag/builder/component/reader/markdown_reader.py](file:///Users/simon/project/KAG/kag/builder/component/reader/markdown_reader.py#L542) `context = {"before_text": ..., "after_text": ...}`
- 但检索侧却按 **camelCase** 取和查（与 `NetOperatorQA.schema` 声明的 `beforeText(前缀)` 一致）：
  - [table_retriever.py](file:///Users/simon/project/KAG/kag/common/tools/algorithm_tool/chunk_retriever/table_retriever.py#L120) `before_text = node_dict["beforeText"]`（硬下标 → 实际节点是 `before_text` 时抛 `KeyError`）
  - [table_retriever.py](file:///Users/simon/project/KAG/kag/common/tools/algorithm_tool/chunk_retriever/table_retriever.py#L86) `search_vector(property_key="beforeText", ...)`（索引字段实际为 `_before_text_vector`）
- 向量字段由 [get_vector_field_name](file:///Users/simon/project/KAG/kag/common/utils.py#L214) 生成：`f"{property_key}_vector"` 再 `to_snake_case`，故 camelCase 属性名与 snake 存储天然错位。

**解决方案**：
1. 读属性兼容两种命名（推荐，最小改动）：
   ```python
   before_text = node_dict.get("before_text", node_dict.get("beforeText", ""))
   after_text  = node_dict.get("after_text",  node_dict.get("afterText",  ""))
   ```
2. 检索向量统一用 snake_case（与索引字段 `_before_text_vector` 对齐）：
   ```python
   property_key="before_text"   # 同一文件 L86/L92 的 "beforeText"/"afterText" 改为 snake_case
   ```
3. 根本修法：为 Table 型构建链统一走 snake_case 命名，并在 schema 声明与映射里保持一致，避免两套命名。

---

## 2. #718 / #747 — 向量化阶段 `TypeError: 'NoneType' object is not iterable`

**状态**：`[已定位]` KAG Python（#747 traceback 直接落在 [batch_vectorizer.py](file:///Users/simon/project/KAG/kag/builder/component/vectorizer/batch_vectorizer.py#L496) 的 `_ainvoke → _agenerate_embedding_vectors`）；#718 为同一 Python 异常经 pemja 桥接抛到服务端 `KagVectorizerAsyncTask.java`。

**根因 A（崩溃点）**：异步批量向量化把每个 batch 的任务结果直接拍平，未对 `None` 做防护：
```python
# _agenerate_dense_vectors / _agenerate_sparse_vectors
results = await asyncio.gather(*tasks)
return [item for sublist in results for item in sublist]   # 任一 avectorize 返回 None → TypeError
```
只要任一 `avectorize(...)` 返回 `None`，`results` 中就含 `None`，拍平时即抛 `'NoneType' object is not iterable`（与 #747 报错完全一致）。

**根因 B（None 的来源，二级）**：部分向量化实现没有校验返回，服务异常/空结果时会返回 `None`。例：[sparse_bge_m3_model.py](file:///Users/simon/project/KAG/kag/common/vectorize_model/sparse_bge_m3_model.py#L75) `_decode_response_data` 对 `res_map.get("resultMap").get("result")` 未判空。

**根因 C（潜在正确性 Bug）**：异步路径里构建了 `sub_texts`（把空文本替换为 `"none"`），但调用时却用了未替换的 `texts[start:end]`（[batch_vectorizer.py L180](file:///Users/simon/project/KAG/kag/builder/component/vectorizer/batch_vectorizer.py#L180) / L209），与同步路径不一致。

**解决方案（KAG Python → 主修）**

① **崩溃点（必改）**：把 `_agenerate_dense_vectors` / `_agenerate_sparse_vectors` 的拍平改成「先校验、再展开」，任一 `avectorize` 返回 `None` 时给出带批次的明确 `ValueError`，而不是默默抛 `TypeError`：

```python
def _coalesce_vectors(self, results, texts):
    """results 中任一 sublist 为 None/空时，暴露具体批次，便于定位是哪路模型。
    texts 须与 sub_texts 一一对应（去重后顺序需保持一致）。"""
    out = []
    for text, sublist in zip(texts, results):
        if sublist is None:
            raise ValueError(
                f"[BatchVectorizer] vectorizer returned None for batch "
                f"(first text: {(text or '')[:50]!r}); check the embedding "
                f"service/model config and response."
            )
        out.extend(sublist)
    return out

# _agenerate_dense_vectors / _agenerate_sparse_vectors 尾部：
results = await asyncio.gather(*tasks)
return self._coalesce_vectors(results, sub_texts)   # texts 取与 results 同序的子批次
```

② **修复异步 `sub_texts` 错位（潜在正确性 Bug）**：同步路径用替换后的 `sub_texts`，异步却传了未替换的 `texts[start:end]`，统一改传 `sub_texts`：

```python
sub_texts = [t if t.strip() else "none" for t in texts[start:end]]
...
tasks.append(asyncio.create_task(dense_vectorizer.avectorize(sub_texts)))
```

③ **模型契约层兜底（治本方向）**：约定 `VectorizeModelABC.avectorize/vectorize`「非空 batch 必须返回同长度结果」；实现返回前校验，`None`/长度不符即抛 `ValueError`，由 ① 统一拦截。示例（sparse_bge_m3 的空值来源）：

```python
# kag/common/vectorize_model/sparse_bge_m3_model.py `_decode_response_data`
res_map = response.json()
result = (res_map.get("resultMap") or {}).get("result")
if result is None:
    raise ValueError(f"embedding response missing 'resultMap.result': {res_map}")
result_values = json.loads(result)
```

**补充（服务端侧 #718，openspg Java）**：`KagVectorizerAsyncTask.java` 捕获 pemja 抛出的 `TypeError` 时，把 Python 异常消息原样落到任务 trace log，并附带 vectorizer 名与 batch 大小，便于在 docker 快速开始里直接定位是哪路 embedding 返回了 None：

```java
} catch (Exception e) {
    log.error("invoke vector Exception: vectorizer={}, batchSize={}, cause={}",
        vectorizerName, batchSize, e.getMessage(), e);
    throw new RuntimeException("invoke vector Exception", e);
}
```

---

## 3. #704 — NER 中文 Schema 拼接，LLM 返回中文类型

**状态**：`[已定位]` KAG Python

**根因**：[kag/builder/prompt/medical/ner.py](file:///Users/simon/project/KAG/kag/builder/prompt/medical/ner.py#L53) 的 `medical_ner` Prompt 用的 `SchemaClient(...).extract_types(language)`，返回的是 Schema 的**展示名（中文别名）**，不是 **SPG 类型英文标识**：
```python
self.schema = SchemaClient(...).extract_types(kag_project_config.language)
self.template = Template(self.template).safe_substitute(schema=self.schema)
```
于是 prompt 里 `"schema": ['特医食品','医学术语',...]`，LLM 输出的 `category` 也是中文，后续映射/对齐阶段无法映射回英文类型标识（`Disease`/`Medicine`…）。

**对照**：`default_ner`([default/ner.py L151-163](file:///Users/simon/project/KAG/kag/builder/prompt/default/ner.py#L151)) 已经正确——用 `.load()` 遍历字典的 **key（英文类型名）** 并过滤 `Index` 类型。

**解决方案**：将 `medical/ner.py` 改为与 `default_ner` 一致，使用英文类型标识：
```python
self.schema = [
    name for name, value in SchemaClient(
        host_addr=kag_project_config.host_addr,
        project_id=kag_project_config.project_id,
    ).load().items()
    if value.spg_type_enum != SpgTypeEnum.Index
]
```
（如确需在 prompt 内同时给中文别名，可再附带一张 标识↔别名 映射表，但 `category` 字段必须回填英文标识。）

---

## 4. #721 — `McpExecutor` 缺 `kag_project_config`

**状态**：`[已定位]` KAG Python，**已在 v0.8.0 修复**（本地 HEAD 即含该修复，对应上游 PR #736，commit `fdab15b3`）。

**根因（原）**：使用 MCP **HTTP store_path** 时，`download_data()` 需要访问 `self.kag_project_config.ckpt_dir`（用来拼下载目录），但旧版 `McpExecutor.__init__` 没有初始化该属性，仅在其父类/其它路径里初始化，导致属性缺失。

**现状（已修复）**：[mcp_executor.py](file:///Users/simon/project/KAG/kag/solver/executor/mcp/mcp_executor.py#L39) 在 `__init__` 中显式注入：
```python
task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
kag_config = KAGConfigAccessor.get_config(task_id)
self.kag_project_config = kag_config.global_config
self.mcp_file_path = self.download_data(store_path)
```

**建议**：
1. 反馈用户直接升级到含 #736 的版本（≥0.8.0）即可。
2. [mcp_executor.py L91](file:///Users/simon/project/KAG/kag/solver/executor/mcp/mcp_executor.py#L91) 的 `def schema(self, ...)` 被写在了类定义之外（缩进错误），实为模块级函数引用未定义 `self`，一旦调用即报错——建议顺带修正为类方法并补 `@ExecutorABC` 相关装饰，或删除。

---

## 5. #732 — eval 检索/读取阶段服务端 NPE

**状态**：`[已定位]` openspg Java 服务端

**根因（修正）**：检索/读取同步任务存在 **「无防空解引用」**：通过 `builderJobService.getById(invokerId)` / `retrievalService.getById(id)` 取对象后不做判空即调用。当 eval 流程派发任务的 `invokerId` 指向不存在的记录（或用例未走标准 builder 构建）时会返回 null，随后解引用即抛裸 NPE。**两个候选空值**（无法仅凭 stack trace 二选一，需运行态确认）：
- `builderJob` 为 null → `builderJob.getRetrievals()` NPE
  - 文件：`server/core/scheduler/service/.../task/sync/builder/RetrievalSyncTask.java`
- `retrievalService.getById(id)` 返回 null → `retrieval.getName()` NPE（`RetrievalSyncTask` 循环内同样未判空）

**读取链路**：`KagReaderSyncTask.readSource`(:72) → `builder/.../physical/utils/CommonUtils.readSource`(:197) → `common/util CommonUtils.getScannerReaderConfig`(:274) `JSON.parseObject(job.getExtension())`（`job==null` → NPE）；后续 `getKagBuilderInput(builderJob, ...)`(:422) 同样未判空。

**解决方案（openspg Java）**

① **`RetrievalSyncTask.submit` —— 对两处空值都判空**（`builderJob` + `retrieval`）：
```java
@Override
public SchedulerEnum.TaskStatus submit(TaskExecuteContext context) {
  SchedulerJob job = context.getJob();
  BuilderJob builderJob = builderJobService.getById(Long.valueOf(job.getInvokerId()));
  if (builderJob == null) {
    context.addTraceLog("builderJob %s not found, skip retrieval", job.getInvokerId());
    return SchedulerEnum.TaskStatus.FINISH;   // 或 FAILURE + 明确原因
  }
  String retrievals = builderJob.getRetrievals();
  if (StringUtils.isBlank(retrievals)) {
    context.addTraceLog("index not set");
    return SchedulerEnum.TaskStatus.FINISH;
  }
  List<Long> retrievalList = JSON.parseObject(retrievals, new TypeReference<List<Long>>() {});
  Project project = projectService.queryById(job.getProjectId());
  for (Long id : retrievalList) {
    Retrieval retrieval = retrievalService.getById(id);
    if (retrieval == null) {
      context.addTraceLog("retrieval %s not found, skip", id);
      continue;   // 不再抛 NPE
    }
    context.addTraceLog("update index(%s) schema", retrieval.getName());
    String schemaDesc = retrieval.getSchemaDesc();
    if (StringUtils.isBlank(schemaDesc)) {
      continue;
    }
    SchemaDraft schemaDraft = getSpgSchema(project, schemaDesc);
    SchemaAlterRequest request = new SchemaAlterRequest();
    request.setProjectId(project.getId());
    request.setSchemaDraft(schemaDraft);
    schemaManager.alterSchema(request);
    context.addTraceLog("update index(%s) schema succeed", retrieval.getName());
  }
  return SchedulerEnum.TaskStatus.FINISH;
}
```

② **`KagReaderSyncTask.submit` —— 入口对 `builderJob` 判空**，避免把 null 传进 `readSource`：
```java
@Override
public SchedulerEnum.TaskStatus submit(TaskExecuteContext context) {
  SchedulerJob job = context.getJob();
  BuilderJob builderJob = builderJobService.getById(Long.valueOf(job.getInvokerId()));
  if (builderJob == null) {
    context.addTraceLog("builderJob %s not found, skip reader", job.getInvokerId());
    return SchedulerEnum.TaskStatus.FINISH;
  }
  List<ChunkRecord.Chunk> chunks = readSource(context, builderJob);
  // ... 原逻辑
}
```

③ **读取桥接层兜底**（`common/util CommonUtils`）：`getScannerReaderConfig` 与 `getKagBuilderInput` 对 `job == null` 走「空配置」而非崩溃，作为双重保险：
```java
// getScannerReaderConfig
JSONObject builderExtension = job == null
    ? new JSONObject()
    : JSON.parseObject(job.getExtension());
...
// getKagBuilderInput
if (builderJob == null) {
  return "";   // 由上层判定为无输入并安全跳过
}
String input = builderJob.getFileUrl();
```

④ **调度侧治理（治本）**：追查 eval 流程为何会派发无对应 builder job 的 `RetrievalSyncTask`/`KagReaderSyncTask`，确认其 `invokerId` 生成规则；在 eval 入口为这类「无构建记录」的检索任务显式建一条占位 job 或复用既有 job，避免依赖「判空兜底」掩盖根因。

---

## 6. #720 — solver 复现 HotpotQA：kgGraph 为空 / EM·F1·hit 过低

**状态**：`[已定位-数据流]` KAG Python；分数问题属配置复现范畴。

**根因（图为空）**：[lf_kg_retriever_template.py 的 `_find_entities`](file:///Users/simon/project/KAG/kag/solver/executor/retriever/local_knowledge_base/kag_retriever/kag_component/kg_cs/lf_kg_retriever_template.py#L35) 只在两种情况下填充 kg_graph：
1. kg_graph 里已有该别名实体；
2. 实体链接 `el.invoke(...)`（查询**向量/图索引**）有命中的话才写入。

若未先构建知识库索引（用户自述「没导入外部图谱 / 没构建 content 索引」或没跑 builder），`el.invoke` 返回 `[]` → 本节点 `head/tail_entities` 为空 → [`_retrieved_on_graph` 直接 `return []`](file:///Users/simon/project/KAG/kag/solver/executor/retriever/local_knowledge_base/kag_retriever/kag_component/kg_cs/lf_kg_retriever_template.py#L165)。这不是代码错，而是缺少构建前置步骤。

**指数过低（EM/F1/hit≈0）**：HotpotQA 的 2-hop 复现强依赖与论文一致的索引、NER/EL 模型、solver「思考」模型、温度与 prompt 配置；大量 open issue 里低分多源于配置/模型不一致，而非单个代码缺陷。

**解决方案**：
1. 复现前必须先用对应 corpus 构建内容+图谱索引（跑完整 builder，确保 `retrievals`/index 已注入），再跑 `eva.py`。
2. 改进可用性：当 EL 无命中导致图子问题为空时，日志显式提示「kgGraph empty：未命中实体链接 / 索引未构建」，并把该子问题降级走 chunk/RC 检索而非静默返回空（`kag_hybrid_executor` 已具备混合回退，可配置开启）。
3. 建议官方在 `kag/open_benchmark/hotpotqa` 附带与论文一致的一键构建+评测配置，减少配置漂移。

---

## 7. #737 — 实体 id/name 写入图库时标点被过滤

**状态**：`[推测]` openspg 服务端（本地 KAG Python 无此过滤逻辑）

**现象**：`30cm/s→30cm s`、`1.1 m→1 1 m`（`.`、`/` 被删除/替换为空格）。

**分析**：KAG Python 侧抽取到的是原始 `name`，写入图库时 SPG 实体 **id 由 name 派生**，标点规范化发生在 openspg 服务端计算实体 id / 图写入（EntityWriter/名称标准化，或图存储 provider 对节点 key 的清理）环节，不在本仓库的 Python 代码里。

**解决方案（待服务端确认）**：
1. 定位 openspg 服务端 `name→id` 派生 / 图写入时的标点清洗逻辑（搜索对 `.`、`/` 等字符的规整处理），将保留标点改为可配置项。
2. 若只想保留原样的读取展示，可确保 `name` 属性/独立字段保存原始字符串（`id` 仍用规范化形式），在 UI 与检索按 `name` 展示。

---

## 8. #753 — Planner 输出中文显示名而非 Schema 英文标识

**状态**：`[推测-设计层]` 与 #704 同源家族：Schema 的**中文展示名（别名）**从规划/检索链路泄漏进非 UI 层，取代了英文类型标识（`生产线/主键` ≠ `ProductionLine.id`），导致实体主键与关系查询失败。

**分析**：该 issue 作者本身列举了一整条链路（rewrite_prompt 缺失、`retrievals=NULL`、index 未注入、`retrievers=[]`、网页 Planner 生成中文伪 Schema…），是跨「规划/检索/索引注入」三层的一致性问题，根源仍是「该用英文标识的地方混入了展示名」。

**解决方案（与 #704 同一原则）**：
1. 规划与检索全程只使用 SPG **英文标识**（同 #704 改用 `.load()` 的 key）；展示名仅用于 UI 渲染层。
2. 在 LF 重写/实体链接处维护 标识↔别名 映射，把任何中文别名先归一到英文标识再下发检索（`kag_lf_rewriter`）。
3. 补齐 issue 作者点出的前置链路：`kag_thinker.yaml` 缺失 `rewrite_prompt`、应用绑定知识库后 `index_list` 自动注入、`builder_job.retrievals` 为空 等为空时的兜底与告警，避免静默退化为 `[]`。

---

## 附：改动文件清单（按所属仓库）

KAG Python（本仓库）：
- `kag/common/tools/algorithm_tool/chunk_retriever/table_retriever.py`（#685）
- `kag/builder/component/vectorizer/batch_vectorizer.py`（#718/#747）
- `kag/common/vectorize_model/*`（#718/#747 的 None 来源校验）
- `kag/builder/prompt/medical/ner.py`（#704）
- `kag/solver/executor/mcp/mcp_executor.py`（#721 附带的 `schema` 方法错位）
- `kag/solver/executor/retriever/.../kg_cs/lf_kg_retriever_template.py` + 混合回退（#720 可观测性）

OpenSPG/openspg（Java 服务端）：
- `server/core/scheduler/service/.../task/sync/builder/RetrievalSyncTask.java`（#732）
- `server/core/scheduler/service/.../task/sync/builder/KagReaderSyncTask.java`（#732）
- `builder/core/.../physical/utils/CommonUtils.java`、`common/util/.../CommonUtils.java`（#732）
- 图写入/实体名标准化（#737，待确认文件）

---

*生成说明：本报告基于本地 HEAD=fdab15b3 的 KAG v0.8.0 源码与 openspg master 服务端源码进行静态根因分析；标注为「推测」的条目建议在对应服务端文件确认后落地。*