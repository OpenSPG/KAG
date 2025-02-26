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
import argparse
import tempfile

from git import Repo
from kag.bin.base import Command
from kag.common.registry import Registrable

from openai import NotFoundError


@Command.register("submit_builder_job")
class BuilderJobSubmit(Command):
    def add_to_parser(self, subparsers: argparse._SubParsersAction):

        parser = subparsers.add_parser(
            "builder", help="Submit distributed builder jobs to cluster"
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
            required=True,
            type=str,
            help="Python entry script path. \n"
            "Will be executed as: python <entry_script>",
        )

        parser.add_argument(
            "--num_workers",
            type=int,
            default=1,
            help="Number of parallel worker instances. \n",
        )

        parser.add_argument(
            "--num_gpus",
            type=int,
            default=1,
            help="GPUs per worker. Requires NVIDIA CUDA-enabled cluster. \n",
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
        if args.validity_check:
            BuilderJobSubmit.validity_check(args)
        if args.init_script is not None:
            cmds.append("sh {args.init_script}")
        entry_cmd = f"python {args.entry_script}"
        cmds.append(entry_cmd)

        command = " && ".join(cmds)
        print(f"command = {command}")
