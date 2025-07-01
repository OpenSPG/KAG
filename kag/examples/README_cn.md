# KAG 示例

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. 前置条件

参考文档 [快速开始](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) 安装 KAG 及其依赖的 OpenSPG server，了解开发者模式 KAG 的使用流程。

## 2. 创建知识库

### 2.1 新建项目

#### Step 1：进入 examples 目录

```bash
cd kag/examples
```

#### Step 2：编辑项目配置

```bash
vim ./example_config.yaml
```

```yaml
#------------project configuration start----------------#
openie_llm: &openie_llm
  api_key: key
  base_url: https://api.deepseek.com
  model: deepseek-chat
  type: maas

chat_llm: &chat_llm
  api_key: key
  base_url: https://api.deepseek.com
  model: deepseek-chat
  type: maas

vectorize_model: &vectorize_model
  api_key: key
  base_url: https://api.siliconflow.cn/v1/
  model: BAAI/bge-m3
  type: openai
  vector_dimensions: 1024
vectorizer: *vectorize_model

log:
  level: INFO

project:
  biz_scene: default
  host_addr: http://127.0.0.1:8887
  id: "1"
  language: en
  namespace: TwoWikiTest
#------------project configuration end----------------#

#------------kag-builder configuration start----------------#
kag_builder_pipeline:
  chain:
    type: unstructured_builder_chain # kag.builder.default_chain.DefaultUnstructuredBuilderChain
    extractor:
      type: schema_free_extractor # kag.builder.component.extractor.schema_free_extractor.SchemaFreeExtractor
      llm: *openie_llm
      ner_prompt:
        type: default_ner # kag.builder.prompt.default.ner.OpenIENERPrompt
      std_prompt:
        type: default_std # kag.builder.prompt.default.std.OpenIEEntitystandardizationdPrompt
      triple_prompt:
        type: default_triple # kag.builder.prompt.default.triple.OpenIETriplePrompt
    reader:
      type: dict_reader # kag.builder.component.reader.dict_reader.DictReader
    post_processor:
      type: kag_post_processor # kag.builder.component.postprocessor.kag_postprocessor.KAGPostProcessor
    splitter:
      type: length_splitter # kag.builder.component.splitter.length_splitter.LengthSplitter
      split_length: 100000
      window_length: 0
    vectorizer:
      type: batch_vectorizer # kag.builder.component.vectorizer.batch_vectorizer.BatchVectorizer
      vectorize_model: *vectorize_model
    writer:
      type: kg_writer # kag.builder.component.writer.kg_writer.KGWriter
  num_threads_per_chain: 1
  num_chains: 16
  scanner:
    type: 2wiki_dataset_scanner # kag.builder.component.scanner.dataset_scanner.MusiqueCorpusScanner
#------------kag-builder configuration end----------------#

#------------kag-solver configuration start----------------#
search_api: &search_api
  type: openspg_search_api #kag.solver.tools.search_api.impl.openspg_search_api.OpenSPGSearchAPI

graph_api: &graph_api
  type: openspg_graph_api #kag.solver.tools.graph_api.impl.openspg_graph_api.OpenSPGGraphApi

exact_kg_retriever: &exact_kg_retriever
  type: default_exact_kg_retriever # kag.solver.retriever.impl.default_exact_kg_retriever.DefaultExactKgRetriever
  el_num: 5
  llm_client: *chat_llm
  search_api: *search_api
  graph_api: *graph_api

fuzzy_kg_retriever: &fuzzy_kg_retriever
  type: default_fuzzy_kg_retriever # kag.solver.retriever.impl.default_fuzzy_kg_retriever.DefaultFuzzyKgRetriever
  el_num: 5
  vectorize_model: *vectorize_model
  llm_client: *chat_llm
  search_api: *search_api
  graph_api: *graph_api

chunk_retriever: &chunk_retriever
  type: default_chunk_retriever # kag.solver.retriever.impl.default_fuzzy_kg_retriever.DefaultFuzzyKgRetriever
  llm_client: *chat_llm
  recall_num: 10
  rerank_topk: 10

kag_solver_pipeline:
  memory:
    type: default_memory # kag.solver.implementation.default_memory.DefaultMemory
    llm_client: *chat_llm
  max_iterations: 3
  reasoner:
    type: default_reasoner # kag.solver.implementation.default_reasoner.DefaultReasoner
    llm_client: *chat_llm
    lf_planner:
      type: default_lf_planner # kag.solver.plan.default_lf_planner.DefaultLFPlanner
      llm_client: *chat_llm
      vectorize_model: *vectorize_model
    lf_executor:
      type: default_lf_executor # kag.solver.execute.default_lf_executor.DefaultLFExecutor
      llm_client: *chat_llm
      force_chunk_retriever: true
      exact_kg_retriever: *exact_kg_retriever
      fuzzy_kg_retriever: *fuzzy_kg_retriever
      chunk_retriever: *chunk_retriever
      merger:
        type: default_lf_sub_query_res_merger # kag.solver.execute.default_sub_query_merger.DefaultLFSubQueryResMerger
        vectorize_model: *vectorize_model
        chunk_retriever: *chunk_retriever
  generator:
    type: default_generator # kag.solver.implementation.default_generator.DefaultGenerator
    llm_client: *chat_llm
    generate_prompt:
      type: resp_simple # kag/examples/2wiki/solver/prompt/resp_generator.py
  reflector:
    type: default_reflector # kag.solver.implementation.default_reflector.DefaultReflector
    llm_client: *chat_llm

#------------kag-solver configuration end----------------#
```

您需要更新其中的生成模型配置 ``openie_llm`` 和 ``chat_llm`` 和表示模型配置 ``vectorize_model``。

您需要设置正确的 ``api_key``。如果使用的模型供应商和模型名与默认值不同，您还需要更新 ``base_url`` 和 ``model``。

#### Step 3：创建项目（与产品模式中的知识库一一对应）

```bash
knext project create --config_path ./example_config.yaml
```

#### Step 4：目录初始化

创建项目之后会在 ``kag/examples`` 目录下创建一个与 ``project`` 配置中 ``namespace`` 字段同名的目录（示例中为 ``TwoWikiTest``），并完成 KAG 项目代码框架初始化。

用户可以修改下述文件的一个或多个，完成业务自定义图谱构建 & 推理问答。

```text
.
├── builder
│   ├── __init__.py
│   ├── data
│   │   └── __init__.py
│   ├── indexer.py
│   └── prompt
│       └── __init__.py
├── kag_config.yaml
├── reasoner
│   └── __init__.py
├── schema
│   ├── TwoWikiTest.schema
│   └── __init__.py
└── solver
    ├── __init__.py
    ├── data
    │   └── __init__.py
    └── prompt
        └── __init__.py
```

### 2.2 更新项目（Optional）

如果有配置变更，可以参考本节内容，更新配置信息到服务端。

#### Step 1：进入项目目录

```bash
cd kag/examples/TwoWikiTest
```

#### Step 2：编辑项目配置

**注意**：由不同表示模型生成的 embedding 向量差异较大，``vectorize_model`` 配置在项目创建后建议不再更新；如有更新 ``vectorize_model`` 配置的需求，请创建一个新项目。

```bash
vim ./kag_config.yaml
```

#### Step 3：运行命令

配置修改后，需要使用 ``knext project update`` 命令将本地配置信息更新到 OpenSPG 服务端。

```bash
knext project update --proj_path .
```

## 3. 导入文档

### Step 1：进入项目目录

```bash
cd kag/examples/TwoWikiTest
```

### Step 2：获取语料数据

2wiki 数据集的测试语料数据为 ``kag/examples/2wiki/builder/data/2wiki_corpus.json``，有 6119 篇文档，和 1000 个问答对。为了迅速跑通整个流程，目录下还有一个 ``2wiki_corpus_sub.json`` 文件，只有 3 篇文档，我们以该小规模数据集为例进行试验。

将其复制到 ``TwoWikiTest`` 项目的同名目录下：

```bash
cp ../2wiki/builder/data/2wiki_sub_corpus.json builder/data
```

### Step 3：编辑 schema（Optional）

编辑 ``schema/TwoWikiTest.schema`` 文件，schema 文件格式参考 [声明式 schema](https://openspg.yuque.com/ndx6g9/0.6/fzhov4l2sst6bede) 相关章节。

### Step 4：提交 schema 到服务端

```bash
knext schema commit
```

### Step 5：执行构建任务

在 ``builder/indexer.py`` 文件中定义任务构建脚本：

```python
import os
import logging
from kag.common.registry import import_modules_from_path

from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)


def buildKB(file_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    runner.invoke(file_path)

    logger.info(f"\n\nbuildKB successfully for {file_path}\n\n")


if __name__ == "__main__":
    import_modules_from_path(".")
    dir_path = os.path.dirname(__file__)
    # 将 file_path 设置为之前准备好的语料文件路径
    file_path = os.path.join(dir_path, "data/2wiki_sub_corpus.json")

    buildKB(file_path)
```

运行 ``indexer.py`` 脚本完成非结构化数据的图谱构建。

```bash
cd builder
python indexer.py
```

构建脚本启动后，会在当前工作目录下生成任务的 checkpoint 目录，记录了构建链路的 checkpoint 和统计信息。

```text
ckpt
├── chain
├── extractor
├── kag_checkpoint_0_1.ckpt
├── postprocessor
├── reader
└── splitter
```

通过以下命令查看抽取任务统计信息，如每个文档抽取出多少点 / 边。

```bash
less ckpt/kag_checkpoint_0_1.ckpt
```

通过以下命令可以查看有多少文档数据被成功写入图数据库。

```bash
wc -l ckpt/kag_checkpoint_0_1.ckpt
```

KAG 框架基于 checkpoint 文件提供了断点续跑的功能。如果由于程序出错或其他外部原因（如 LLM 余额不足）导致任务中断，可以重新执行 indexer.py，KAG 会自动加载 checkpoint 文件并复用已有结果。

### Step 6：结果检查

当前，OpenSPG-KAG 在产品端已提供 [知识探查](https://openspg.yuque.com/ndx6g9/0.6/fw4ge5c18tyfl2yq) 能力，以及对应的 API 文档 [HTTP API Reference](https://openspg.yuque.com/ndx6g9/0.6/zde1yunbb8sncxtv)。

![KAG Knowledge Inspection Diagram](/_static/images/examples/kag-knowledge-inspection-diag.png)

## 4. 推理问答

### Step 1：进入项目目录

```bash
cd kag/examples/TwoWikiTest
```

### Step 2：编写问答脚本

```bash
vim ./solver/qa.py
```

将以下内容粘贴到 ``qa.py`` 中。

```python
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from kag.common.benchmarks.evaluate import Evaluate
from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path

from kag.common.checkpointer import CheckpointerManager

logger = logging.getLogger(__name__)


class EvaFor2wiki:
    """
    init for kag client
    """

    def __init__(self):
        pass

    """
        qa from knowledge base,
    """

    def qa(self, query):
        resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
        answer, traceLog = resp.run(query)

        logger.info(f"\n\nso the answer for '{query}' is: {answer}\n\n")
        return answer, traceLog

if __name__ == "__main__":
    import_modules_from_path("./prompt")
    evalObj = EvaFor2wiki()

    evalObj.qa("Which Stanford University professor works on Alzheimer's?")
```

### Step 3：运行命令

```bash
cd solver
python qa.py
```

## 5. 其他内置案例

可进入 [kag/examples](.) 目录体验源码中自带的案例。

* [musique](./musique/README_cn.md)（多跳问答）
* [twowiki](./2wiki/README_cn.md)（多跳问答）
* [hotpotqa](./hotpotqa/README_cn.md)（多跳问答）
* [黑产挖掘](./riskmining/README_cn.md)
* [企业供应链](./supplychain/README_cn.md)
* [医疗图谱](./medicine/README_cn.md)

