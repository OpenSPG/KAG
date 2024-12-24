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

from setuptools import setup, find_packages

package_name = "openspg-kag"

# version
cwd = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(cwd, "KAG_VERSION"), "r") as rf:
    version = rf.readline().strip("\n").strip()

# license
license = ""
with open(os.path.join(cwd, "LICENSE"), "r") as rf:
    line = rf.readline()
    while line:
        line = line.strip()
        if line:
            license += "# " + line + "\n"
        else:
            license += "#\n"
        line = rf.readline()

setup(
    name=package_name,
    version=version,
    description="kag",
    url="https://github.com/OpenSPG/openspg",
    packages=find_packages(
        where=".",
        exclude=[
            ".*test.py",
            "*_test.py",
            "*_debug.py",
            "*.txt",
            "tests",
            "tests.*",
            "configs",
            "configs.*",
            "test",
            "test.*",
            "*.tests",
            "*.tests.*",
            "*.pyc",
            "__pycache__",
            "*/__pycache__/*",
        ],
    ),
    python_requires=">=3.8",
    install_requires=[
        r.strip()
        for r in open("requirements.txt", "r")
        if not r.strip().startswith("#")
    ],
    include_package_data=True,
    package_data={
        "bin": ["*"],
    },
    entry_points={
        "console_scripts": [
            "kag = kag.bin.kag_cmds:main",
            "knext=knext.command.knext_cli:_main",
        ]
    },
)

