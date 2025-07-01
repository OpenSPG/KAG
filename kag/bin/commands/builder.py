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
import argparse
import tempfile
import requests
from git import Repo
from kag.bin.base import Command
from kag.common.registry import Registrable
from kag.common.conf import KAG_PROJECT_CONF
from kag.common.utils import bold, green, reset
from openai import NotFoundError


@Command.register("submit_builder_job")
class BuilderJobSubmit(Command):
    def add_to_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "builder", help="Submit distributed builder jobs to cluster"
        )

        parser.add_argument(
            "--user_number",
            type=str,
            help="User number",
        )

        parser.add_argument(
            "--host_addr",
            default=None,
            help="Host address of SPG server.",
        )

        parser.add_argument(
            "--project_id",
            default=None,
            help="Project ID in SPG server.",
        )

        parser.add_argument(
            "--git_url",
            required=True,
            type=str,
            help="Git repository URL containing project source code (supports SSH/HTTP)",
        )

        parser.add_argument(
            "--commit_id",
            required=True,
            type=str,
            help="Git commit id containing project source code (supports SSH/HTTP)",
        )

        parser.add_argument(
            "--init_script",
            default=None,
            help="Bash script path for worker container initialization.",
        )

        parser.add_argument(
            "--entry_script",
            type=str,
            default=None,
            help="Python entry script path. \n"
            "Will be executed as: python <entry_script>",
        )

        parser.add_argument(
            "--index_url",
            type=str,
            default=None,
            help="Base URL of the Python Package Index. \n",
        )

        parser.add_argument("--image", type=str, help="Worker image.")
        parser.add_argument("--pool", type=str, help="Worker resource pool.")

        parser.add_argument(
            "--num_workers",
            type=int,
            default=1,
            help="Number of parallel worker instances. \n",
        )

        parser.add_argument(
            "--num_gpus",
            type=int,
            default=0,
            help="GPUs per worker. Requires NVIDIA CUDA-enabled cluster. \n",
        )

        parser.add_argument(
            "--gpu_type",
            type=str,
            default=None,
            help="GPU type. Requires NVIDIA CUDA-enabled cluster. \n",
        )

        parser.add_argument(
            "--num_cpus", type=int, default=8, help="CPU cores per worker."
        )

        # 存储资源配置
        parser.add_argument(
            "--memory",
            type=int,
            default=8,
            help="Memory allocation per worker (GB).",
        )

        parser.add_argument(
            "--storage",
            type=int,
            default=50,
            help="Ephemeral disk space per worker (GB).",
        )

        parser.add_argument(
            "--env",
            type=str,
            default="",
            help="Environment variables, with each variable formatted as key=value and separated by commas: k1=v1, k2=v2",
        )

        parser.add_argument(
            "--validity_check",
            action="store_true",
            help="Perform validity check.",
        )

        parser.set_defaults(func=self.get_handler())

    @staticmethod
    def get_cls(cls_name):
        interface_classes = Registrable.list_all_registered(with_leaf_classes=False)
        for item in interface_classes:
            if item.__name__ == cls_name:
                return item
        raise ValueError(f"class {cls_name} is not a valid kag configurable class")

    @staticmethod
    def validity_check(args: argparse.Namespace):
        with tempfile.TemporaryDirectory() as local_dir:
            repo = Repo.clone_from(args.git_url, local_dir)
            # parsed_url = parse(args.git_url)
            repo.git.checkout(args.commit_id)
            if args.init_script is not None:
                if not os.path.exists(os.path.join(local_dir, args.init_script)):
                    raise NotFoundError(
                        f"init script {args.init_script} not found in git repo"
                    )
            if not os.path.exists(os.path.join(local_dir, args.entry_script)):
                raise ValueError(
                    f"entry script {args.entry_script} not found in git repo"
                )

    @staticmethod
    def handler(args: argparse.Namespace):
        work_dir = "src"
        cmds = [
            f"git clone {args.git_url} {work_dir}",
            f"cd {work_dir}",
            f"git checkout {args.commit_id}",
        ]
        if args.index_url:
            cmds.append(f"pip install -e . -i {args.index_url}")
        else:
            cmds.append("pip install -e .")

        if args.validity_check:
            BuilderJobSubmit.validity_check(args)
        if args.init_script is not None:
            cmds.append(f"sh {args.init_script}")

        if args.entry_script is not None:
            entry_script_dir = os.path.dirname(args.entry_script)
            entry_script_name = os.path.basename(args.entry_script)
            entry_cmd = f"cd {entry_script_dir} && python {entry_script_name}"
            cmds.append(entry_cmd)

        command = " && ".join(cmds)

        envs = {}
        if args.env:
            kvs = args.env.split(",")
            for kv in kvs:
                key, value = kv.split("=")
                envs[key.strip()] = value.strip()

        if args.project_id is not None:
            project_id = int(args.project_id)
        else:
            project_id = int(KAG_PROJECT_CONF.project_id)
        req = {
            "projectId": project_id,
            "command": command,
            "workerNum": args.num_workers,
            "workerCpu": args.num_cpus,
            "workerGpu": args.num_gpus,
            "workerMemory": args.memory * 1024,
            "workerStorage": args.storage * 1024,
            "envs": envs,
        }
        if args.num_gpus > 0 and args.gpu_type:
            req["workerGpuType"] = args.gpu_type

        if args.image:
            req["image"] = args.image
        if args.pool:
            req["workerPool"] = args.pool

        if args.user_number:
            req["userNumber"] = args.user_number

        if args.host_addr is not None:
            host_addr = args.host_addr.rstrip("/")
        else:
            host_addr = KAG_PROJECT_CONF.host_addr.rstrip("/")
        url = host_addr + "/public/v1/builder/kag/submit"
        rsp = requests.post(url, json=req)
        rsp.raise_for_status()
        print(f"{bold}{green}Success submit job to server, info:{reset}")
        print(json.dumps(rsp.json(), indent=4))
