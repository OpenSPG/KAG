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
import asyncio
import threading
from typing import Dict
from tqdm.asyncio import tqdm
from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, generate_hash_id
from kag.common.checkpointer import CheckpointerManager
from kag.interface import KAGBuilderChain, ScannerABC
from kag.interface.builder.base import BuilderComponentData
from kag.builder.model.sub_graph import SubGraph
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from kag.common.registry import import_modules_from_path


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
        max_concurrency: int = 100,
        **kwargs,
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
        self.max_concurrency = max_concurrency
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.ckpt_dir = kag_project_config.ckpt_dir

        self.checkpointer = CheckpointerManager.get_checkpointer(
            {
                "type": "txt",
                "ckpt_dir": self.ckpt_dir,
                "rank": self.scanner.sharding_info.get_rank(),
                "world_size": self.scanner.sharding_info.get_world_size(),
            }
        )

    def invoke(self, input):
        """
        Processes the input data using the builder chain in parallel and manages checkpoints.

        Args:
            input: The input data to be processed.
        """

        def process(data, data_id, data_abstract):
            try:
                result = self.chain.invoke(
                    data,
                    max_workers=self.num_threads_per_chain,
                )
                return data, data_id, data_abstract, result
            except Exception:
                traceback.print_exc()
                return None

        futures = []
        success = 0
        try:
            with ThreadPoolExecutor(self.num_chains) as executor:
                for item in self.scanner.generate(input):
                    item_id, item_abstract = generate_hash_id_and_abstract(item)
                    # if self.checkpointer.exists(item_id):
                    #     continue
                    fut = executor.submit(
                        process,
                        item,
                        item_id,
                        item_abstract,
                    )
                    futures.append(fut)

                success = 0
                from tqdm import tqdm

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
                            if isinstance(item, BuilderComponentData):
                                item = item.data
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
                        success += 1
        except:
            traceback.print_exc()
        CheckpointerManager.close()
        msg = (
            f"{bold}{red}Done process {len(futures)} records, with {success} successfully processed and {len(futures)-success} failures encountered.\n"
            f"Please access this file to obtain detailed task statistics.{reset}"
        )
        print(msg)

    async def ainvoke(self, input):
        """
        Processes the input data using the builder chain in parallel and manages checkpoints.

        Args:
            input: The input data to be processed.
        """

        async def process(data, data_id, data_abstract):
            try:
                result = await self.chain.ainvoke(data)
                if result is not None:
                    info = {}
                    num_nodes = 0
                    num_edges = 0
                    num_subgraphs = 0
                    for item in result:
                        if isinstance(item, BuilderComponentData):
                            item = item.data
                        if isinstance(item, SubGraph):
                            num_nodes += len(item.nodes)
                            num_edges += len(item.edges)
                            num_subgraphs += 1

                    info = {
                        "num_nodes": num_nodes,
                        "num_edges": num_edges,
                        "num_subgraphs": num_subgraphs,
                    }
                    await asyncio.to_thread(
                        lambda: self.checkpointer.write_to_ckpt(
                            data_id, {"abstract": data_abstract, "graph_stat": info}
                        )
                    )
                return 1
            except Exception:
                logger.error(f"Failed to process data {data_abstract}, info:")
                traceback.print_exc()
                return 0

        async def producer(queue):
            for item in self.scanner.generate(input):
                await queue.put(item)
            for _ in range(self.max_concurrency):
                await queue.put(None)

        async def consumer(queue, pbar):
            total = 0
            checkpointed = 0
            success = 0
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break
                total += 1
                item_id, item_abstract = generate_hash_id_and_abstract(item)
                if not self.checkpointer.exists(item_id):
                    flag = await process(item, item_id, item_abstract)
                    success += flag

                else:
                    checkpointed += 1
                pbar.update(1)
                queue.task_done()

            return total, checkpointed, success

        pbar = tqdm(total=self.scanner.size(input))
        queue = asyncio.Queue(maxsize=self.max_concurrency * 10)

        producer_task = asyncio.create_task(producer(queue))
        consumer_tasks = [
            asyncio.create_task(consumer(queue, pbar))
            for _ in range(self.max_concurrency)
        ]
        await producer_task
        await queue.join()
        results = await asyncio.gather(*consumer_tasks)

        total = sum(t for t, _, _ in results)
        checkpointed = sum(c for _, c, _ in results)
        success = sum(s for _, _, s in results)
        pbar.close()
        CheckpointerManager.close()
        msg = (
            f"{bold}{red}Done process {total} records, with {checkpointed} found in checkpoint, "
            f"{success} successfully processed and {total-checkpointed-success} failures encountered.\n"
            f"The log file is located at {self.checkpointer._ckpt_file_path}. "
            f"Please access this file to obtain detailed task statistics.{reset}"
        )
        print(msg)


BuilderChainRunner.register("base", as_default=True)(BuilderChainRunner)


@BuilderChainRunner.register("stream")
class BuilderChainStreamRunner(BuilderChainRunner):
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
        register_path: str = None,
        **kwargs,
    ):
        """
        Initializes the BuilderChainRunner instance.

        Args:
            scanner (ScannerABC): The source scanner to generate input data.
            chain (KAGBuilderChain): The builder chain to process the input data.
            num_chains (int, optional): The number of parallel threads to use, with each thread launching a builder chain instance. Defaults to 2.
            num_threads_per_chain (int, optional): The number of parallel workers within a builder chain. Defaults to 8.
            ckpt_dir (str, optional): The directory to store checkpoint files. Defaults to "./ckpt".
            register_path (str, optional): The path to register modules. Defaults to None.
        """
        self.scanner = scanner
        self.chain = chain
        self.num_chains = num_chains
        self.num_threads_per_chain = num_threads_per_chain
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        kag_project_config = kag_config.global_config
        self.ckpt_dir = kag_project_config.ckpt_dir
        self.register_path = register_path
        # self.checkpointer = CheckpointerManager.get_checkpointer(
        #     {
        #         "type": "txt",
        #         "ckpt_dir": self.ckpt_dir,
        #         "rank": self.scanner.sharding_info.get_rank(),
        #         "world_size": self.scanner.sharding_info.get_world_size(),
        #     }
        # )
        self.processed_chunks = CheckpointerManager.get_checkpointer(
            {
                "type": "diskcache",
                "ckpt_dir": os.path.join(self.ckpt_dir, "chain"),
                "rank": self.scanner.sharding_info.get_rank(),
                "world_size": self.scanner.sharding_info.get_world_size(),
            }
        )
        self._local = threading.local()

    @staticmethod
    def _init_worker(chain_config, num_threads, register_path):
        global process_chain, process_num_threads
        logger.info(f"jincheng__register_path: {register_path}")
        import_modules_from_path(register_path)
        # 在每个进程中重新创建chain
        process_chain = KAGBuilderChain.from_config(chain_config)
        process_num_threads = num_threads

    @staticmethod
    def process(data, data_id, data_abstract, processed_chunk_keys):
        try:
            global process_chain, process_num_threads
            result = process_chain.invoke(
                data,
                max_workers=process_num_threads,
                processed_chunk_keys=processed_chunk_keys,
            )
            return data, data_id, data_abstract, result
        except Exception:
            traceback.print_exc()
            return None

    def invoke(self, input):
        """
        Processes the input data using the builder chain in a streaming fashion.
        This method works with a blocking/continuous generator by processing results
        as they complete while continuing to accept new items from the stream.

        Args:
            input: The input data to be processed.
        """

        print(f"Processing stream from {input}")
        success = 0
        submitted = 0

        # 不使用manager.dict()，使用普通字典
        futures_map = {}

        # 获取chain的配置
        chain_config = self.chain.to_config()

        try:
            with ProcessPoolExecutor(
                max_workers=self.num_chains,
                initializer=self._init_worker,
                initargs=(chain_config, self.num_threads_per_chain, self.register_path),
            ) as executor:

                def generate_items():
                    for item in self.scanner.generate(input):
                        try:
                            item_id, item_abstract = generate_hash_id_and_abstract(item)

                            # 提交任务
                            fut = executor.submit(
                                BuilderChainStreamRunner.process,
                                item,
                                item_id,
                                item_abstract,
                                self.processed_chunks.keys(),
                            )
                            nonlocal submitted
                            # 在本地字典中存储Future对象
                            futures_map[fut] = (submitted, item_id, item_abstract)
                            submitted += 1
                        except Exception:
                            traceback.print_exc()
                            continue

                # Start the generator thread
                gen_thread = threading.Thread(target=generate_items, daemon=True)
                gen_thread.start()

                # Process results as they complete
                with tqdm(desc="Processing stream", position=0) as pbar:
                    while gen_thread.is_alive() or futures_map:
                        # Process any completed futures
                        done_futures = []
                        for fut in list(futures_map.keys()):
                            if fut.done():
                                done_futures.append(fut)

                        for fut in done_futures:
                            # 从本地字典获取信息
                            submitted_id, item_id, item_abstract = futures_map.pop(fut)

                            # 处理结果
                            try:
                                result = fut.result()
                            except Exception:
                                traceback.print_exc()
                                continue

                            if result is not None:
                                item, item_id, item_abstract, chain_output = result

                                # Process the result and update checkpoints
                                num_nodes, num_edges, num_subgraphs = 0, 0, 0
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

                                # info = {
                                #     "num_nodes": num_nodes,
                                #     "num_edges": num_edges,
                                #     "num_subgraphs": num_subgraphs,
                                # }
                                # self.checkpointer.write_to_ckpt(
                                #     item_id,
                                #     {"abstract": item_abstract, "graph_stat": info},
                                # )
                                success += 1
                                pbar.update(1)
                                pbar.set_description(
                                    f"Processed: {success}/{submitted}"
                                )

                        # Small sleep to avoid busy-waiting
                        if not done_futures:
                            import time

                            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nInterrupted by user. Saving progress...")
        except Exception:
            traceback.print_exc()

        CheckpointerManager.close()
        msg = (
            f"{bold}{red}Done processing stream. {success} successfully processed out of {submitted} submitted tasks.\n"
            f"Please access this file to obtain detailed task statistics.{reset}"
        )
        print(msg)
