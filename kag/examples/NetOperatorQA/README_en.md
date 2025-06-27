# KAG NetOperatorQA

[English](./README_en.md) |
[简体中文](./README.md)

NetOperatorQA is a knowledge question-answering dataset focused on the telecommunications operator domain. In the era of rapid digital transformation and intelligent communication services, telecommunications operators' business scope continues to expand, covering 5G network construction, cloud computing services, big data applications, IoT business, digital government, and many other fields. Knowledge Graph (KG), as a structured information management approach, provides comprehensive factual and data support for operator business through semantic associations and contextual understanding. When dealing with complex technical documents, annual reports, business specifications, and operational data, fast and accurate information retrieval capabilities are particularly important.

This dataset focuses on telecommunications operator knowledge Q&A tasks, aiming to retrieve business facts from large-scale knowledge graphs related to operators to answer relevant questions. We define the input as a specific operator business question, and the output as facts extracted from the knowledge graph to answer the question. Data sources include various forms of Markdown documents such as operator annual reports, quarterly reports, technical white papers, and business introduction documents.

In this example, we demonstrate building a knowledge graph for the NetOperatorQA dataset, then using [KAG](https://arxiv.org/abs/2409.13731) to generate answers for evaluation questions and calculate EM and F1 metrics by comparing with standard answers.

## Implementation

For the NetOperatorQA telecommunications operator knowledge Q&A dataset, our implementation follows the KAG (Knowledge-Augmented Generation) framework with the following specific steps:

### Data Preprocessing and Schema Definition
We first preprocess the raw operator data provided by NetOperatorQA. At this stage, we process various formats of Markdown documents including operator annual reports, technical documents, and business introductions, performing preliminary classification or structured organization of information to facilitate subsequent graph construction.

Based on the KAG framework and OpenSPG's schema modeling specifications, we abstract core concepts in the telecommunications operator domain (such as network technology, business products, financial data, technical indicators, partners, etc.), defining corresponding Entity Types, Relation Types, and their Properties. This definition is embodied in the schema/NetOperatorQA.schema file and submitted to the OpenSPG graph database as the structural blueprint for the knowledge graph.

## 1. Prerequisites

Refer to the documentation [Quick Start](https://openspg.yuque.com/ndx6g9/0.6/quzq24g4esal7q17) to install KAG and its dependent OpenSPG server, and understand the usage process of KAG in developer mode.

## Configuration Instructions

### Index Construction Configuration
In the configuration file, you can enable different combinations of extractors based on your needs:

**Complete Index Construction (Recommended for Production)**:
- chunk_extractor - Basic text chunks
- outline_extractor - Outline structure
- summary_extractor - Semantic summaries
- table_extractor - Table data
- atomic_query_extractor - Atomic queries

**Fast Construction (Suitable for Testing and Development)**:
- Use only basic text chunk extractor

### Retrieval Configuration Options
The system provides two main retrieval configurations:

**Simple Retrieval Mode**: Suitable for direct fact queries
- Use only vector retriever for fast response

**Complete Retrieval Mode**: Suitable for complex reasoning queries
- Atomic query retriever
- Outline retriever
- Summary retriever
- Vector retriever
- Table retriever


## 2. Reproduction Steps

### Step 1: Enter Example Directory

```bash
cd kag/examples/NetOperatorQA
```

### Step 2: Configure Models

Update the generation model configurations `openie_llm` and `chat_llm` and the representation model configuration `vectorize_model` in [kag_config.yaml](./kag_config.yaml).

You need to set the correct `api_key`. If the model provider and model name differ from the default values, you also need to update `base_url` and `model`.

### Step 3: Initialize Project

Initialize the project first.

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### Step 4: Submit Schema

Execute the following command to submit schema [NetOperatorQA.schema](./schema/NetOperatorQA.schema).

```bash
knext schema commit
```

### Step 5: Build Knowledge Graph

Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph.

```bash
cd builder && python indexer.py && cd ..
```

### Step 6: Execute Q&A Task

Execute [eval.py](./solver/eval.py) in the [solver](./solver) directory to generate answers and calculate EM and F1 metrics.

```bash
cd solver && python eval.py && cd ..
```

### Step 7: (Optional) Cleanup

To delete checkpoints, execute the following commands.

```bash
rm -rf ./builder/ckpt
rm -rf ./solver/ckpt
```

## Dataset and Technical Features

### Dataset Features
The NetOperatorQA dataset has the following characteristics:

1. **Multiple Document Types**: Contains annual reports (AY series), technical white papers (BZ series), business introductions (BY series), network construction (BW series), technical standards (BT series), financial data (BF series), and other types of documents

2. **Rich Business Domains**: Covers telecommunications operator core business areas including 5G networks, cloud computing, big data, IoT, industrial internet, digital government, smart cities, etc.

3. **Structured Information**: Contains multi-dimensional structured information including financial indicators, technical parameters, business data, partnership relationships, etc.

4. **Temporal Nature**: Data covers reports and data from multiple time periods, facilitating trend analysis and historical comparisons

5. **Professional Content**: Involves telecommunications technical terminology, business models, financial indicators, and other professional content, placing high demands on the model's domain understanding capabilities

### Technical Architecture Features

1. **Multi-Index System**: Constructs multiple index types including text chunk index, outline index, summary index, table index, atomic query index, etc.

2. **Hybrid Retrieval Strategy**: Combines vector retrieval, structured retrieval, semantic retrieval, and other retrieval methods

3. **Adaptive Reasoning**: Automatically selects simple reasoner or complex reasoner based on question complexity

4. **Domain Optimization**: Customized planners and prompt templates specifically for telecommunications operator domain characteristics

5. **Configurable Architecture**: Supports flexible configuration of different extractor, retriever, and reasoner combinations

6. **Performance Optimization**: Provides fast mode and complete mode to balance effectiveness and efficiency 