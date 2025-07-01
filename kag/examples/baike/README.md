# KAG Example: BaiKe

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/baike
```

### Step 2: Configure models

Update the generative model configurations ``openie_llm`` and ``chat_llm`` and the representational model configuration ``vectorize_model`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``s. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

### Step 3: Project initialization

Initiate the project with the following command.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4: Commit the schema

Execute the following command to commit the schema [BaiKe.schema](./schema/BaiKe.schema).

```bash
knext schema commit
```

### Step 5: Build the knowledge graph

Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph.

```bash
cd builder && python indexer.py && cd ..
```

### Step 6: Execute the QA tasks

Execute [eval.py](./solver/eval.py) in the [solver](./solver) directory to ask demo questions and view the answers and trace logs.

```bash
cd solver && python eval.py && cd ..
```

We have implemented an MCP server in KAG, allowing the knowledge base built by KAG to be exposed via the MCP server for integration with agents that support the MCP protocol. Please refer to [KAG MCP Server Example: BaiKe](./mcp_server.md).

### Step 7: (Optional) Cleanup

To delete the checkpoints, execute the following command.

```bash
rm -rf ./builder/ckpt
```

