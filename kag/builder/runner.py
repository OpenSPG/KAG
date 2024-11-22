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
from datetime import datetime
from tqdm import tqdm
from kag.common.registry import Registrable
from kag.interface import KAGBuilderChain, SourceReaderABC
from concurrent.futures import ThreadPoolExecutor, as_completed


def generate_hash_id(value):
    if isinstance(value, dict):
        sorted_items = sorted(value.items())
        key = str(sorted_items)
    else:
        key = value
    if isinstance(key, str):
        key = key.encode("utf-8")
    hasher = hashlib.sha256()
    hasher.update(key)

    return hasher.hexdigest()


class CKPT:
    ckpt_file_name = "kag-runner.ckpt"

    def __init__(self, path: str):
        self.path = path
        self.ckpt_file_path = os.path.join(self.path, CKPT.ckpt_file_name)
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

    def add(self, data_id: str):
        if self.is_processed(data_id):
            return
        now = datetime.now()
        self.writer.write(json.dumps({"id": data_id, "time": str(now)}))
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

        self.ckpt = CKPT(self.ckpt_dir)

    def invoke(self, input):
        def process(chain, data, data_id):
            try:

                result = chain.invoke(data, max_workers=self.chain_level_num_paralle)
                return result, data_id
            except Exception:
                traceback.print_exc()
                return None

        self.ckpt.open()
        futures = []
        print(f"Processing {input}")
        with ThreadPoolExecutor(self.num_parallel) as executor:
            for item in self.reader.invoke(input):
                item_id = generate_hash_id(item)
                if self.ckpt.is_processed(item_id):
                    continue
                fut = executor.submit(process, self.chain, item, item_id)
                futures.append(fut)
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Progress",
                position=0,
            ):
                result = future.result()
                if result is not None:
                    chain_output, item_id = result
                    self.ckpt.add(item_id)
        self.ckpt.close()


BuilderChainRunner.register("base", as_default=True)(BuilderChainRunner)
