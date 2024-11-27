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
import json
import traceback
import logging
from typing import Any, Dict
from datetime import datetime
from tqdm import tqdm

from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, generate_hash_id
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


class CKPT:
    """
    CKPT class is responsible for managing checkpoint files, which is used for record/resume KAG tasks.

    This class provides methods to load, save, and check the status of data processing checkpoints.
    """

    ckpt_file_name = "kag-runner-{}-{}.ckpt"

    def __init__(self, path: str, rank: int = 0, world_size: int = 1):
        """
        Initializes the CKPT instance.

        Args:
            path (str): The path where the checkpoint file is stored.
            rank (int, optional): The rank of the process. Defaults to 0.
            world_size (int, optional): The total number of processes. Defaults to 1.
        """
        self.rank = rank
        self.world_size = world_size
        self.path = path
        self.ckpt_file_path = os.path.join(
            self.path, CKPT.ckpt_file_name.format(rank, world_size)
        )
        self._ckpt = set()
        if os.path.exists(self.ckpt_file_path):
            self.load()

    def load(self):
        """
        Loads the checkpoint data from the file.
        """
        for rank in range(self.world_size):
            ckpt_file_path = os.path.join(
                self.path, CKPT.ckpt_file_name.format(rank, self.world_size)
            )
            with open(ckpt_file_path, "r") as reader:
                for line in reader:
                    data = json.loads(line)
                    self._ckpt.add(data["id"])

    def is_processed(self, data_id: str):
        """
        Checks if a data ID has already been processed.

        Args:
            data_id (str): The data ID to check.

        Returns:
            bool: True if the data ID has been processed, False otherwise.
        """
        return data_id in self._ckpt

    def open(self):
        """
        Opens the checkpoint file for appending.
        """
        self.writer = open(self.ckpt_file_path, "a")

    def add(self, data_id: str, data_abstract: str, info: Any):
        """
        Adds a new entry to the checkpoint file.

        Args:
            data_id (str): The data ID to add.
            data_abstract (str): The abstract of the data.
            info (Any): Additional information to store.
        """
        if self.is_processed(data_id):
            return
        now = datetime.now()
        self.writer.write(
            json.dumps(
                {
                    "id": data_id,
                    "abstract": data_abstract,
                    "info": info,
                    "timestamp": str(now),
                }
            )
        )
        self.writer.write("\n")
        self.writer.flush()

    def close(self):
        """
        Closes the checkpoint file.
        """
        self.writer.flush()
        self.writer.close()


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
        ckpt_dir: str = "./ckpt",
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
        self.ckpt_dir = ckpt_dir
        if not os.path.exists(self.ckpt_dir):
            os.makedirs(self.ckpt_dir, exist_ok=True)

        self.ckpt = CKPT(
            self.ckpt_dir,
            self.reader.sharding_info.get_rank(),
            self.reader.sharding_info.get_world_size(),
        )
        msg = (
            f"{bold}{red}The checkpoint file is located at {self.ckpt.ckpt_file_path}. "
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

        self.ckpt.open()
        futures = []
        print(f"Processing {input}")
        with ThreadPoolExecutor(self.num_parallel) as executor:
            for item in self.reader.generate(input):
                item_id, item_abstract = generate_hash_id_and_abstract(item)
                if self.ckpt.is_processed(item_id):
                    continue
                fut = executor.submit(process, self.chain, item, item_id, item_abstract)
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
                    self.ckpt.add(item_id, item_abstract, info)
        self.ckpt.close()


BuilderChainRunner.register("base", as_default=True)(BuilderChainRunner)
