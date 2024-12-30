# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.


import os
import traceback
import logging
import threading
from typing import Dict
from tqdm import tqdm

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, generate_hash_id
from kag.common.checkpointer import CheckpointerManager
from kag.interface import KAGBuilderChain, ScannerABC

from kag.builder.model.sub_graph import SubGraph
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()


def str_abstract(value: str):
    """
    Abstracts a string value by returning the base name if it is a file path, or the first 10 characters otherwise.

    Args:
        value (str): The string value to be abstracted.

    Returns:
        str: The abstracted string value.
    """
    if os.path.exists(value):
        return os.path.basename(value)
    return value[:10]


def dict_abstract(value: Dict):
    """
    Abstracts each value in a dictionary by converting it to a string and then abstracting the string.

    Args:
        value (Dict): The dictionary to be abstracted.

    Returns:
        Dict: The abstracted dictionary.
    """
    output = {}
    for k, v in value.items():
        output[k] = str_abstract(str(v))
    return output


def generate_hash_id_and_abstract(value):
    hash_id = generate_hash_id(value)
    if isinstance(value, dict):
        abstract = dict_abstract(value)
    else:
        abstract = str_abstract(value)
    return hash_id, abstract


class BuilderChainRunner(Registrable):
    """
    A class that manages the execution of a KAGBuilderChain with parallel processing and checkpointing.

    This class provides methods to initialize the runner, process input data, and manage checkpoints for tracking processed data.
    """

    def __init__(
        self,
        scanner: ScannerABC,
        chain: KAGBuilderChain,
        num_chains: int = 2,
        num_threads_per_chain: int = 8,
    ):
        """
        Initializes the BuilderChainRunner instance.

        Args:
            scanner (ScannerABC): The source scanner to generate input data.
            chain (KAGBuilderChain): The builder chain to process the input data.
            num_chains (int, optional): The number of parallel threads to use, with each thread launching a builder chain instance. Defaults to 2.
            num_threads_per_chain (int, optional): The number of parallel workers within a builder chain. Defaults to 8.
            ckpt_dir (str, optional): The directory to store checkpoint files. Defaults to "./ckpt".
        """
        self.scanner = scanner
        self.chain = chain
        self.num_chains = num_chains
        self.num_threads_per_chain = num_threads_per_chain
        self.ckpt_dir = KAG_PROJECT_CONF.ckpt_dir

        self.checkpointer = CheckpointerManager.get_checkpointer(
            {
                "type": "txt",
                "ckpt_dir": self.ckpt_dir,
                "rank": self.scanner.sharding_info.get_rank(),
                "world_size": self.scanner.sharding_info.get_world_size(),
            }
        )
        self.processed_chunks = CheckpointerManager.get_checkpointer(
            {
                "type": "zodb",
                "ckpt_dir": os.path.join(self.ckpt_dir, "chain"),
                "rank": self.scanner.sharding_info.get_rank(),
                "world_size": self.scanner.sharding_info.get_world_size(),
            }
        )
        self._local = threading.local()

    def invoke(self, input):
        """
        Processes the input data using the builder chain in parallel and manages checkpoints.

        Args:
            input: The input data to be processed.
        """

        # def process(thread_local, chain_conf, data, data_id, data_abstract):
        #     try:
        #         if not hasattr(thread_local, "chain"):
        #             if chain_conf:
        #                 thread_local.chain = KAGBuilderChain.from_config(chain_conf)
        #             else:
        #                 thread_local.chain = self.chain
        #         result = thread_local.chain.invoke(
        #             data, max_workers=self.num_threads_per_chain
        #         )
        #         return data, data_id, data_abstract, result
        #     except Exception:
        #         traceback.print_exc()
        #         return None

        def process(data, data_id, data_abstract):
            try:
                result = self.chain.invoke(
                    data,
                    max_workers=self.num_threads_per_chain,
                    processed_chunk_keys=self.processed_chunks.keys(),
                )
                return data, data_id, data_abstract, result
            except Exception:
                traceback.print_exc()
                return None

        futures = []
        print(f"Processing {input}")
        success = 0
        try:
            with ThreadPoolExecutor(self.num_chains) as executor:
                for item in self.scanner.generate(input):
                    item_id, item_abstract = generate_hash_id_and_abstract(item)
                    if self.checkpointer.exists(item_id):
                        continue
                    fut = executor.submit(
                        process,
                        item,
                        item_id,
                        item_abstract,
                    )
                    futures.append(fut)

                success = 0
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="Progress",
                    position=0,
                ):
                    result = future.result()
                    if result is not None:
                        item, item_id, item_abstract, chain_output = result
                        info = {}
                        num_nodes = 0
                        num_edges = 0
                        num_subgraphs = 0
                        for item in chain_output:
                            if isinstance(item, SubGraph):
                                num_nodes += len(item.nodes)
                                num_edges += len(item.edges)
                                num_subgraphs += 1
                            elif isinstance(item, dict):

                                for k, v in item.items():
                                    self.processed_chunks.write_to_ckpt(k, k)
                                    if isinstance(v, SubGraph):
                                        num_nodes += len(v.nodes)
                                        num_edges += len(v.edges)
                                        num_subgraphs += 1

                        info = {
                            "num_nodes": num_nodes,
                            "num_edges": num_edges,
                            "num_subgraphs": num_subgraphs,
                        }
                        self.checkpointer.write_to_ckpt(
                            item_id, {"abstract": item_abstract, "graph_stat": info}
                        )
                        success += 1
        except:
            traceback.print_exc()
        CheckpointerManager.close()
        msg = (
            f"{bold}{red}Done process {len(futures)} records, with {success} successfully processed and {len(futures)-success} failures encountered.\n"
            f"The log file is located at {self.checkpointer._ckpt_file_path}. "
            f"Please access this file to obtain detailed task statistics.{reset}"
        )
        print(msg)


BuilderChainRunner.register("base", as_default=True)(BuilderChainRunner)
