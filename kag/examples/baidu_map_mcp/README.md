# KAG Example: Baidu Map MCP

[English](./README.md) |
[简体中文](./README_cn.md)

## 1. Precondition

Please refer to [Quick Start](https://openspg.yuque.com/ndx6g9/cwh47i/rs7gr8g4s538b1n7) to install KAG and its dependency OpenSPG server, and learn about using KAG in developer mode.

Then register and create a server-side API Key (AK) at [Baidu Maps Open Platform](https://lbsyun.baidu.com/apiconsole/key). Be sure to enable "MCP (SSE)" service for best performance.

## 2. Steps to reproduce

### Step 1: Enter the example directory

```bash
cd kag/examples/baidu_map_mcp
```

### Step 2: Configure models

Update the generative model configurations ``chat_llm``  in [kag_config.yaml](./kag_config.yaml).

You need to fill in correct ``api_key`` and ``BAIDU_MAPS_API_KEY``. If your model providers and model names are different from the default values, you also need to update ``base_url`` and ``model``.

### Step 3: Execute the QA tasks

In the directory, execute [google_web_search_client.py](./google_web_search_client.py) 

```bash
python baidu_map_mcp_client.py
```

Example problems:

1. What will the weather be like tomorrow in the West Lake District of Hangzhou?
2. What is the self-driving route from Ant A space in Hangzhou to Ant S space in Shanghai?
3. What is the latitude and longitude of Shanghai Hongqiao Railway Station?

After launch, please input the questions you want to ask, we will retrieve the relevant information through baidu map, and then return the results to you.

