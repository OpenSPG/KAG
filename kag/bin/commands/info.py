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
from tabulate import tabulate
from kag.bin.base import Command
from kag.common.registry import Registrable
from kag.common.utils import reset, bold, red, green, blue


@Command.register("register_info")
class ListRegisterInfo(Command):
    def add_to_parser(self, subparsers: argparse._SubParsersAction):
        parser = subparsers.add_parser(
            "interface", help="Show the interface info of the KAG components."
        )
        parser.add_argument("--cls", help="class name to query")
        parser.add_argument(
            "--list", help="list all component interfaces in KAG", action="store_true"
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
    def handle_list(args: argparse.Namespace):
        interface_classes = Registrable.list_all_registered(with_leaf_classes=False)
        data = []
        for cls in interface_classes:
            data.append([cls.__name__, cls.__module__])
        headers = [f"{bold}{red}class{reset}", f"{bold}{red}module{reset}"]
        msg = (
            f"{bold}{red}Below are the interfaces provided by KAG."
            f"For detailed information on each class, please use the command `kag interface --cls $class_name`{reset}"
        )
        print(msg)
        print(tabulate(data, headers, tablefmt="grid"))

    @staticmethod
    def handle_cls(args: argparse.Namespace):
        cls_obj = ListRegisterInfo.get_cls(args.cls)
        if not issubclass(cls_obj, Registrable):
            raise ValueError(f"class {args.cls} is not a valid kag configurable class")
        availables = cls_obj.list_available_with_detail()
        seg = " " * 20

        deduped_availables = {}
        for register_name, cls_info in availables.items():
            cls = cls_info["class"]
            if cls not in deduped_availables:
                deduped_availables[cls] = [register_name]
            else:
                deduped_availables[cls].append(register_name)

        print(f"{bold}{red}{seg}Documentation of {args.cls}{seg}{reset}")
        import inspect

        print(inspect.getdoc(cls_obj))
        print(f"{bold}{red}{seg}Registered subclasses of {args.cls}{seg}{reset}")
        visited = set()
        for register_name, cls_info in availables.items():
            cls = cls_info["class"]
            if cls in visited:
                continue
            visited.add(cls)
            print(f"{bold}{blue}[{cls}]{reset}")
            register_names = " / ".join([f'"{x}"' for x in deduped_availables[cls]])
            print(f"{bold}{green}Register Name:{reset} {register_names}\n")

            # print(f"Class Name: {cls_info['class']}")
            print(f"{bold}{green}Documentation:{reset}\n{cls_info['doc']}\n")
            print(f"{bold}{green}Initializer:{reset}\n{cls_info['constructor']}\n")

            required_arguments = []
            for item in cls_info["params"]["required_params"]:
                required_arguments.append(f"  {item}")
            if len(required_arguments) == 0:
                required_arguments = "  No Required Arguments found"
            else:
                required_arguments = "\n".join(required_arguments)
            print(f"{bold}{green}Required Arguments:{reset}\n{required_arguments}\n")

            optional_arguments = []
            for item in cls_info["params"]["optional_params"]:
                optional_arguments.append(f"  {item}")
            if len(optional_arguments) == 0:
                optional_arguments = "  No Optional Arguments found"
            else:
                optional_arguments = "\n".join(optional_arguments)
            print(f"{bold}{green}Optional Arguments:{reset}\n{optional_arguments}\n")
            print(f"{bold}{green}Sample Useage:{reset}\n  {cls_info['sample_useage']}")
            # for k, v in cls_info.items():
            #     print(f"{k}: {v}")
            print("\n")

    @staticmethod
    def handler(args: argparse.Namespace):
        if args.list:
            ListRegisterInfo.handle_list(args)
        else:
            ListRegisterInfo.handle_cls(args)
