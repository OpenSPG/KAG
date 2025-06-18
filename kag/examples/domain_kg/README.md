# KAG Example: DomainKG

[English](./README.md) |
[简体中文](./README_cn.md)

This example provides a case of knowledge injection in the medical domain, where the nodes of the domain knowledge graph are medical terms, and the relationships are defined as "isA". The document contains an introduction to a selection of medical terms.

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/domain_kg
```

### Step 2: Configure models

Update the generative model configurations ``openie_llm`` and ``chat_llm`` and the representive model configuration ``vectorizer_model`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``s. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

### Step 3: Project initialization

Initiate the project with the following command.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4: Commit the schema

Execute the following command to commit the schema [DomainKG.schema](./schema/DomainKG.schema).

```bash
knext schema commit
```

### Step 5: Build the knowledge graph

We first need to inject the domain knowledge graph into the graph database. This allows the PostProcessor component to link the extracted nodes with the nodes of the domain knowledge graph, thereby standardizing them during the construction of the graph from unstructured documents.  

Execute [injection.py](./builder/injection.py) in the [builder](./builder) directory to inject the domain KG.

```bash
cd builder && python injection.py && cd ..
```

Note that KAG provides a special implementation of the ``KAGBuilderChain`` for domain knowledge graph injection, known as the ``DomainKnowledgeInjectChain``, which is registered under the name ``domain_kg_inject_chain``. Since domain knowledge injection does not involve scanning files or directories, you can directly call the ``invoke`` interface of the chain to initiate the task.

Next, execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build KG from unstructured document.

```bash
cd builder && python indexer.py && cd ..
```

### Step 6: Execute the QA tasks

Execute [qa.py](./solver/qa.py) in the [solver](./solver) directory to generate the answer to the question.

```bash
cd solver && python qa.py && cd ..
```

### Step 7: (Optional) Cleanup

To delete the checkpoints, execute the following command.

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

