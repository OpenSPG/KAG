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
# flake8: noqa
import os
import inspect
import logging
import asyncio
import argparse
import yaml
import multiprocessing
from typing import Callable, Any
from kag.bin.base import Command
from kag.common.registry import Registrable, Functor, import_modules_from_path
from kag.common.conf import KAGConstants, init_env
from kag.common.checkpointer import CheckpointerManager

logger = logging.getLogger(__name__)
try:
    multiprocessing.set_start_method("spawn")
except:
    pass


class KAGBenchmark(Registrable):
    def __init__(
        self,
        dataset: str,
        config_file: str,
        index_builder: Functor,
        qa_solver: Functor,
    ):
        self.dataset = dataset
        self.config_file = config_file
        self.job_name = f"{dataset}#{self.config_file}"
        self.index_builder = index_builder
        self.qa_solver = qa_solver

    def prepare_kag_config_file(self):
        old_config_file = KAGConstants.KAG_CONFIG_FILE_NAME
        if os.path.exists(old_config_file):
            with open(old_config_file, "r") as reader:
                old_content = reader.read()

        else:
            old_content = None
        new_config_file = self.config_file
        with open(new_config_file, "r") as reader:
            new_content = reader.read()
        with open(old_config_file, "w") as writer:
            writer.write(new_content)
        logger.info(f"set {KAGConstants.KAG_CONFIG_FILE_NAME} to {self.config_file}")
        if old_content:
            backup_file = f"{KAGConstants.KAG_CONFIG_FILE_NAME}.bak"
            with open(backup_file, "w") as writer:
                writer.write(old_content)

    def pre_invoke(self):
        self.prepare_kag_config_file()

        from kag.common.utils import run_cmd

        cmds = ["knext project restore", "knext schema commit"]
        init_project_cmd = " && ".join(cmds)
        logger.info(f"Init project with command: {init_project_cmd}")
        run_cmd(init_project_cmd)
        init_env(KAGConstants.KAG_CONFIG_FILE_NAME)

    def is_async(self, func: Callable[..., Any]) -> bool:
        """Determines if a callable is an asynchronous function.

        This function checks whether the given callable is defined with 'async def'
        or returns an awaitable object. It handles both function objects and callable
        class instances.

        Args:
            func: A callable object to be checked (function, method, or callable class).

        Returns:
            bool: True if the callable is an async function, False otherwise.

        Examples:
            >>> async def async_func(): pass
            >>> def sync_func(): pass
            >>> is_async(async_func)  # Returns True
            >>> is_async(sync_func)   # Returns False
        """
        if inspect.iscoroutinefunction(func):
            return True
        if inspect.isawaitable(func):
            return True
        if callable(func) and inspect.iscoroutinefunction(
            getattr(func, "__call__", None)
        ):
            return True
        return False

    def invoke(self):
        self.pre_invoke()

        output = {}
        logger.info(
            f"start to run benchmark with dataset {self.dataset} and config {self.config_file}"
        )

        logger.info("Run builder...")
        if self.is_async(self.index_builder):
            result = self.sync_wrapper(self.index_builder())
        else:
            result = self.index_builder()
        output["builder"] = result
        logger.info("Done run builder!")

        logger.info("Run solver...")
        if self.is_async(self.qa_solver):
            result = self.sync_wrapper(self.qa_solver())
        else:
            result = self.qa_solver()
        output["solver"] = result
        logger.info("Done run solver!")
        return output

    @staticmethod
    def sync_wrapper(coro):
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)


def run_benchmark(config, result_queue):
    workdir = config.pop("root_dir")
    print(f"workdir = {workdir}")
    os.chdir(workdir)
    import_modules_from_path("./")
    # import benchmark common component
    import kag.open_benchmark.common_component

    runner = KAGBenchmark.from_config(config)
    result = runner.invoke()
    result_queue.put((runner.job_name, result))


# def run_benchmark(config):
#     workdir = config.pop("root_dir")
#     print(f"workdir = {workdir}")
#     os.chdir(workdir)
#     import_modules_from_path("./")
#     runner = KAGBenchmark.from_config(config)
#     result = runner.invoke()
#     return result


@Command.register("run_benchmark")
class RunBenchmark(Command):
    def add_to_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "benchmark", help="Submit distributed builder jobs to cluster"
        )

        parser.add_argument(
            "--job_config",
            type=str,
            help="job configuration file",
        )
        # parser.add_argument(
        #     "--datasets",
        #     type=str,
        #     help="job names to run",
        # )
        parser.add_argument(
            "--env",
            type=str,
            default="",
            help="Environment variables, with each variable formatted as key=value and separated by commas: k1=v1, k2=v2",
        )
        parser.set_defaults(func=self.get_handler())

    @staticmethod
    def handler(args: argparse.Namespace):
        if not args.job_config:
            config_file = KAGConstants.KAG_CONFIG_FILE_NAME
        else:
            config_file = args.job_config
        with open(config_file, "r") as reader:
            content = reader.read()
            config = yaml.safe_load(content)

        kvs = args.env.split(",")
        for kv in kvs:
            key, value = kv.split("=")
            os.environ[key.strip()] = value.strip()
        datasets = config.keys()
        # results = []
        # for dataset, dataset_config in config.items():
        #     benchmark_config = {"dataset": dataset}
        #     benchmark_config.update(dataset_config)
        #     result = run_benchmark(benchmark_config)
        #     results.append(result)

        ckpt = CheckpointerManager.get_checkpointer(
            {
                "type": "diskcache",
                "ckpt_dir": "./ckpt/Benchmark",
                "rank": 0,
                "world_size": 1,
            }
        )

        result_queue = multiprocessing.Queue()
        ps = []
        results = {}
        for dataset, dataset_config in config.items():
            if ckpt.exists(dataset):
                result = ckpt.read_from_ckpt(dataset)
            else:
                benchmark_config = {"dataset": dataset}
                benchmark_config.update(dataset_config)
                p = multiprocessing.Process(
                    target=run_benchmark,
                    args=(benchmark_config, result_queue),
                )
                ps.append(p)
                p.start()
                p.join()
                result = result_queue.get()
                ckpt.write_to_ckpt(dataset, result)
            results[result[0]] = result[1]
        CheckpointerManager.close()
        print(f"Done benchmark, detail info:\n {results}")
