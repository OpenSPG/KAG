
# Experiments of KAG

## 1. Preparation

### 1.1 Install Neo4j DB

Install Neo4j from https://neo4j.com/ and add default admin account ```user=xxxx; password=yyyy```. 

### 1.2 Download bge model

download beg model file from https://huggingface.co/BAAI/bge-base-en-v1.5 and move the model file into default cache directory.

```tar -zxvf bge-base-en-v1.5 && mv ./bge-base-en-v1.5 ~/.cache/vectorizer/BAAI/```

## 2. Semantic Index Building

### 1.2 Edit config files

```angular2html
[graph_store]
uri = neo4j://localhost:7687
user =  your_user_here
password = your_password_here
database = your_neo4j_db_name_here # configure your db name 

...

[llm]
client_type = maas
base_url = https://api.deepseek.com/beta
api_key = "put your deepseek api key here"
model = deepseek-chat

[indexer]
corpus_path = ./dataset/2wikimultihopqa_corpus.json
with_semantic_sim_edge = True
with_semantic_fix_onto = True
with_semantic_entity_norm = True
with_semantic_hyper_expand = True
similarity_threshold = 0.8
concept_sim_threshold = 0.9

...
```

Build semantic graph index with: 
```shell
python kag_main.py build -c configs/build/semantic_graph.cfg 
```

## 3. Question Answering

Run KAG inference with: 
```shell
python kag_main.py qa -c configs/qa/qa_default.cfg
```

The metrics are saving into file ```./results/qa_default_metrics.json```; 

predict detail will be saved in file ```./results/qa_default_res.json```. 

