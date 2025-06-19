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
import argparse
from kag.bin.base import add_commands


def build_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="subcommand_name",
        title="subcommands",
        help="subcommands supported by kag",
    )
    # add registered commands to parser
    cmds = [
        "register_info",
        "submit_builder_job",
        "run_benchmark",
        "run_kag_mcp_server",
    ]
    add_commands(subparsers, cmds)
    return parser


def main():
    """entry point of script"""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
