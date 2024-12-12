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
from typing import Dict
from tqdm import tqdm

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, generate_hash_id
from kag.common.checkpointer import CheckPointer
from kag.interface import KAGBuilderChain, SourceReaderABC

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
        reader: SourceReaderABC,
        chain: KAGBuilderChain,
        num_parallel: int = 2,
        chain_level_num_paralle: int = 8,
    ):
        """
        Initializes the BuilderChainRunner instance.

        Args:
            reader (SourceReaderABC): The source reader to generate input data.
            chain (KAGBuilderChain): The builder chain to process the input data.
            num_parallel (int, optional): The number of parallel threads to use, with each thread launching a builder chain instance. Defaults to 2.
            chain_level_num_paralle (int, optional): The number of parallel workers within a builder chain. Defaults to 8.
            ckpt_dir (str, optional): The directory to store checkpoint files. Defaults to "./ckpt".
        """
        self.reader = reader
        self.chain = chain
        self.num_parallel = num_parallel
        self.chain_level_num_paralle = chain_level_num_paralle
        self.ckpt_dir = KAG_PROJECT_CONF.ckpt_dir

        self.checkpointer = CheckPointer.from_config(
            {
                "type": "txt",
                "ckpt_dir": self.ckpt_dir,
                "rank": self.reader.sharding_info.get_rank(),
                "world_size": self.reader.sharding_info.get_world_size(),
            }
        )
        msg = (
            f"{bold}{red}The log file is located at {self.checkpointer._ckpt_file_path}. "
            f"Please access this file to obtain detailed task statistics.{reset}"
        )
        print(msg)

    def invoke(self, input):
        """
        Processes the input data using the builder chain in parallel and manages checkpoints.

        Args:
            input: The input data to be processed.
        """

        def process(chain, data, data_id, data_abstract):
            try:
                result = chain.invoke(data, max_workers=self.chain_level_num_paralle)
                return data, data_id, data_abstract, result
            except Exception:
                traceback.print_exc()
                return None

        futures = []
        print(f"Processing {input}")
        try:
            with ThreadPoolExecutor(self.num_parallel) as executor:
                for item in self.reader.generate(input):
                    item_id, item_abstract = generate_hash_id_and_abstract(item)
                    if self.checkpointer.exists(item_id):
                        continue
                    fut = executor.submit(
                        process, self.chain, item, item_id, item_abstract
                    )
                    futures.append(fut)

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
                        info = {
                            "num_nodes": num_nodes,
                            "num_edges": num_edges,
                            "num_subgraphs": num_subgraphs,
                        }
                        self.checkpointer.write_to_ckpt(
                            item_id, {"abstract": item_abstract, "graph_stat": info}
                        )
        except:
            traceback.print_exc()
        self.checkpointer.close()
        self.chain.close_checkpointers()


BuilderChainRunner.register("base", as_default=True)(BuilderChainRunner)
