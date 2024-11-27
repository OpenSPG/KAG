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
import logging
import typing
from kag.common.registry import Registrable

logger = logging.getLogger()


def add_commands(
    subparsers: argparse._SubParsersAction, command_names: typing.List[str] = None
):
    """add commands to subparsers"""
    all_cmds = Command.list_available()
    if command_names is None:
        logger.warn("invalid command_names, will add all available commands.")
        command_names = all_cmds
    for cmd in command_names:
        if cmd not in all_cmds:
            raise ValueError(f"command {cmd} not in available commands {all_cmds}")
        # Command Subclasses doesn't accept init args, so just pass subclass name is OK.
        cls = Command.from_config(cmd)
        cls.add_to_parser(subparsers)


class Command(Registrable):
    def get_handler(self):
        """return handler of current command"""
        return self.handler

    def add_to_parser(self, subparsers: argparse._SubParsersAction):
        """setup accept arguments"""
        raise NotImplementedError("setup_parser not implemented yet.")

    @staticmethod
    def handler(args: argparse.Namespace):
        """function to proces the request."""
        raise NotImplementedError("handler not implemented yet.")
