# KAG Example: MuSiQue

[English](./README.md) |
[简体中文](./README_cn.md)

[MuSiQue](https://arxiv.org/abs/2108.00573) is a multi-hop QA dataset for comprehensive evaluation of reasoning steps. It's used by [KAG](https://arxiv.org/abs/2409.13731) and [HippoRAG](https://arxiv.org/abs/2405.14831) for multi-hop question answering performance evaluation.

Here we demonstrate how to build a knowledge graph for the MuSiQue dataset, generate answers to those evaluation questions with KAG and calculate EM and F1 metrics of the KAG generated answers compared to the ground-truth answers.

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/open_benchmark/musique
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


Execute the following command to commit the schema [MuSiQue.schema](./schema/MuSiQue.schema).

```bash
knext schema commit
```

### Step 5: Build the knowledge graph

Execute [indexer.py](./src/indexer.py) in the [src](./src) directory to build the knowledge graph.

```bash
cd src && python indexer.py && cd ..
```

### Step 6: Execute the QA tasks

Execute [eval.py](./src/eval.py) in the [src](./src) directory to generate the answers and calculate the EM and F1 metrics.

```bash
cd src && python eval.py --qa_file ./data/qa_sub.json && cd ..
```

The generated answers are saved to ``./src/musique_res_*.json``.

The calculated EM and F1 metrics are saved to ``./src/musique_metrics_*.json``.

### Step 7: (Optional) Cleanup

To delete the checkpoints, execute the following command.

```bash
rm -rf ./src/ckpt
```

### Step 8: (Optional) Try the larger datasets

Restart from Step 1 and modify [indexer.py](./src/indexer.py) and [eval.py](./src/eval.py) to try the larger datasets.

