# KAG Example: CSQA

[English](./README.md) |
[简体中文](./README_cn.md)

The [UltraDomain](https://huggingface.co/datasets/TommyChien/UltraDomain/tree/main) ``cs.jsonl`` dataset contains 10 documents in Computer Science and 100 questions with their answers about those documents.

Here we demonstrate how to build a knowledge graph for those documents, generate answers to those questions with KAG and compare KAG generated answers with those from other RAG systems.

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/csqa
```

### Step 2: (Optional) Prepare the data

Download [UltraDomain](https://huggingface.co/datasets/TommyChien/UltraDomain/tree/main) ``cs.jsonl`` and execute [generate_data.py](./generate_data.py) to generate data files in [./builder/data](./builder/data) and [./solver/data](./solver/data). Since the generated files were committed, this step is optional.

```bash
python generate_data.py
```

### Step 3: Configure models

Update the generative model configurations ``openie_llm`` and ``chat_llm`` and the representational model configuration ``vectorize_model`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``s. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

The ``splitter`` and ``num_threads_per_chain`` configurations may also be updated to match with other systems.

### Step 4: Project initialization

Initiate the project with the following command.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 5: Commit the schema

Execute the following command to commit the schema [CsQa.schema](./schema/CsQa.schema).

```bash
knext schema commit
```

### Step 6: Build the knowledge graph

Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph.

```bash
cd builder && python indexer.py && cd ..
```

### Step 7: Execute the QA tasks

Execute [eval.py](./solver/eval.py) in the [solver](./solver) directory to generate the answers.

```bash
cd solver && python eval.py && cd ..
```

### Step 8: (Optional) Cleanup

To delete the checkpoints, execute the following command.

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/csqa_ckpt
```

