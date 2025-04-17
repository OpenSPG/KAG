# KAG Example: AffairQA

[English](./README.md) |
[简体中文](./README_cn.md)

[AffairQA](https://arxiv.org/abs/2011.01060) is a knowledge graph evaluation dataset proposed by the Knowledge Graph team at Zhejiang University. [KAG](https://arxiv.org/abs/2409.13731).

In this example, we demonstrate how to build a knowledge graph for the AffairQA dataset, then use KAG to generate answers for evaluation questions, and calculate EM and F1 metrics by comparing with standard answers.

## 1. Prerequisites

Refer to [Quick Start](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) to install KAG and its dependency OpenSPG server, and understand the development mode usage process of KAG.

## 2. Reproduction Steps

### Step 1: Enter the example directory

```bash
cd kag/open_benchmark/AffairQA
```

### Step 2: Configure Models

Update the generation model configurations `openie_llm` and `chat_llm`, and the representation model configuration `vectorize_model` in [kag_config.yaml](./kag_config.yaml).

You need to set the correct `api_key`. If you're using a different model provider and model name than the defaults, you'll also need to update `base_url` and `model`.

### Step 3: Initialize Project

First, initialize the project.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4: Submit Schema

Execute the following command to submit the schema [AffairQA.schema](./schema/AffairQA.schema).

```bash
knext schema commit
```

### Step 5: Build Knowledge Graph

Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph.

```bash
cd builder && python indexer.py && cd ..
```

### Step 6: Execute QA Task

Execute [eval.py](./solver/eval.py) in the [solver](./solver) directory to generate answers and calculate EM and F1 metrics.

```bash
cd solver && python eval.py && cd ..
```

Generated answers are saved to `./solver/data/res*.json`.

Execute answer evaluation and F1/EM calculation:
```bash
python solver/evalForAffairQA.py --input_file {eval generation answer}
``` 

### Step 7: (Optional) Cleanup

To delete checkpoints, execute the following commands:

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

To delete the KAG project and associated knowledge graph, execute a command similar to the following, replacing the OpenSPG server address and KAG project id with actual values:

```bash
curl http://127.0.0.1:8887/project/api/delete?projectId=1
```