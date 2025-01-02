# KAG Example: MuSiQue

[MuSiQue](https://arxiv.org/abs/2108.00573) is a multi-hop QA dataset
for comprehensive evaluation of reasoning steps. It's used by [KAG](https://arxiv.org/abs/2409.13731)
and [HippoRAG](https://arxiv.org/abs/2405.14831) for multi-hop question answering
performance evaluation.

Here we demonstrate how to build a knowledge graph for the MuSiQue dataset,
generate answers to those evaluation questions with KAG and calculate EM and F1
metrics of the KAG generated answers compared to the ground-truth answers.

## Steps to reproduce

1. Follow the Quick Start guide of KAG to install the OpenSPG server and KAG.

   The following steps assume the Python virtual environment with KAG installed
   is activated and the current directory is [musique](.).

2. (Optional) Update [indexer.py](./builder/indexer.py) and [evaForMusique.py](./solver/evaForMusique.py)
   to use the larger dataset. You may want to skip this step the first time and
   use the small dataset to get started quickly.

3. Update the ``openie_llm``, ``chat_llm`` and ``vectorizer_model`` configurations
   in [kag_config.yaml](./kag_config.yaml) properly.

4. Restore the KAG project.

   ```bash
   knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
   ```

5. Commit the schema.

   ```bash
   knext schema commit
   ```

6. Execute [indexer.py](./builder/indexer.py) in the [builder](./builder) directory to build the knowledge graph.

   ```bash
   cd builder && python indexer.py && cd ..
   ```

7. Execute [evaForMusique.py](./solver/evaForMusique.py) in the [solver](./solver) directory
   to generate the answers and calculate the EM and F1 metrics.

   ```bash
   cd solver && python evaForMusique.py && cd ..
   ```

   The generated answers are saved to ``./solver/musique_res_*.json``.

   The calculated EM and F1 metrics are saved to ``./solver/musique_metrics_*.json``.

8. (Optional) To delete checkpoints, execute the following commands.

   ```bash
   rm -rf ./builder/ckpt
   rm -rf ./solver/ckpt
   ```

   To delete the KAG project and related knowledge graph, execute the following similar command.
   Replace the OpenSPG server address and KAG project id with actual values.

   ```bash
   curl http://127.0.0.1:8887/project/api/delete?projectId=1
   ```

9. (Optional) Restart from Step 2 and try the larger dataset.
