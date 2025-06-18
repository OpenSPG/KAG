# KAG Example: Medical Knowledge Graph (Medicine)

[English](./README.md) |
[简体中文](./README_cn.md)

This example aims to demonstrate how to extract and construct entities and relations in a knowledge graph based on the SPG-Schema using LLMs.

![KAG Medicine Diagram](/_static/images/examples/medicine/kag-medicine-diag.png)

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/medicine
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

Execute the following command to commit the Medical Knowledge Graph schema [Medicine.schema](./schema/Medicine.schema).

```bash
knext schema commit
```

### Step 5: Build the knowledge graph

Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph with domain knowledge importing and schema-free extraction.

```bash
cd builder && python indexer.py && cd ..
```

Check [Disease.csv](./builder/data/Disease.csv) to inspect the descriptions of diseases. Those unstructured descriptions are schema-free extracted by ``extract_runner`` defined in [kag_config.yaml](./kag_config.yaml).

Other structured data in [data](./builder/data) will be imported directly by corresponding builder chains defined in [kag_config.yaml](./kag_config.yaml).

### Step 6: Query the knowledge graph with GQL

You can use the ``knext reasoner`` command to inspect the built knowledge graph.

The query DSL will be executed by the OpenSPG server, which supports ISO GQL.

* Execute the following command to execute DSL directly.

  ```bash
  knext reasoner execute --dsl "
  MATCH
      (s:Medicine.HospitalDepartment)-[p]->(o)
  RETURN
      s.id, s.name
  "
  ```

  The results will be displayed on the screen and saved as CSV to the current directory.

* You can also save the DSL to a file and execute the file.

  ```bash
  knext reasoner execute --file ./reasoner/rule.dsl
  ```

* You can also use the reasoner Python client to query the knowledge graph.

  ```bash
  python ./reasoner/client.py
  ```

### Step 7: Execute the QA tasks

Execute [evaForMedicine.py](./solver/evaForMedicine.py) in the [solver](./solver) directory to ask a demo question in natural languages and view the answer and trace log.

```bash
cd solver && python evaForMedicine.py && cd ..
```

### Step 8: (Optional) Cleanup

To delete the checkpoint, execute the following command.

```bash
rm -rf ./builder/ckpt
```

