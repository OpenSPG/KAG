# KAG Example: Google Web Search MCP

[English](./README.md) |
[简体中文](./README_cn.md)

Here is a Google Web Search MCP that takes the search question entered by the user as input and returns the relevant web page. Here, we only show the execution effect of MCP. If you need to link to KAG for retrieval, please visit OpenSPG to create the corresponding knowledge base and application, and link MCP to KAG and use it.

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/google_web_search_mcp
```

### Step 2: Configure models

Update the generative model configurations ``chat_llm`` in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key``. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

### Step 3: Execute the QA tasks

In the directory, execute [google_web_search_client.py](./google_web_search_client.py) 

```bash
python google_web_search_client.py
```

Example problems:

1. Why is the sky blue?
2. What is Dundar effect?

After launch, please input the questions you want to ask, we will retrieve the relevant web page through Google, and then return the results to you.

