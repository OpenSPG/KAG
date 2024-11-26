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


import hashlib
import os
import json
import traceback
import logging
from typing import Any, Dict
from datetime import datetime
from tqdm import tqdm

from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red
from kag.interface import KAGBuilderChain, SourceReaderABC
from kag.builder.model.sub_graph import SubGraph
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()


def str_abstract(value: str):
    if os.path.exists(value):
        return os.path.basename(value)
    return value[:10]


def dict_abstract(value: Dict):
    output = {}
    for k, v in value.items():
        output[k] = str_abstract(str(v))
    return output


def generate_hash_id(value):
    if isinstance(value, dict):
        sorted_items = sorted(value.items())
        key = str(sorted_items)
        abstract = dict_abstract(value)
    else:
        key = value
        abstract = str_abstract(value)
    if isinstance(key, str):
        key = key.encode("utf-8")
    hasher = hashlib.sha256()
    hasher.update(key)

    return hasher.hexdigest(), abstract


class CKPT:
    ckpt_file_name = "kag-runner-{}-{}.ckpt"

    def __init__(self, path: str, rank: int = 0, world_size: int = 1):
        self.path = path
        self.ckpt_file_path = os.path.join(
            self.path, CKPT.ckpt_file_name.format(rank, world_size)
        )
        self._ckpt = set()
        if os.path.exists(self.ckpt_file_path):
            self.load()

    def load(self):
        with open(self.ckpt_file_path, "r") as reader:
            for line in reader:
                data = json.loads(line)
                self._ckpt.add(data["id"])

    def is_processed(self, data_id: str):
        return data_id in self._ckpt

    def open(self):
        self.writer = open(self.ckpt_file_path, "a")

    def add(self, data_id: str, data_abstract: str, info: Any):
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
        self.writer.flush()
        self.writer.close()


class BuilderChainRunner(Registrable):
    def __init__(
        self,
        reader: SourceReaderABC,
        chain: KAGBuilderChain,
        num_parallel: int = 2,
        chain_level_num_paralle: int = 8,
        ckpt_dir: str = None,
    ):
        self.reader = reader
        self.chain = chain
        self.num_parallel = num_parallel
        self.chain_level_num_paralle = chain_level_num_paralle
        if ckpt_dir is None:
            ckpt_dir = "./ckpt"
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
                item_id, item_abstract = generate_hash_id(item)
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
