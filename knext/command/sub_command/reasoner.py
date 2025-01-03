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
import sys
from pathlib import Path
import yaml
import click

from knext.reasoner.client import ReasonerClient
from knext.common.env import env


@click.option("--file", help="Path of DSL file.")
@click.option("--dsl", help="DSL string enclosed in double quotes.")
@click.option("--output", help="Output file.")
@click.option("--proj_path", help="Path of config.", default="./")
def execute_reasoner_job(file, dsl, output=None, proj_path="./"):
    """
    Submit asynchronous reasoner jobs to server by providing DSL file or string.
    """
    client = ReasonerClient(host_addr=env.host_addr, project_id=int(env.project_id))
    if file and not dsl:
        with open(file, "r") as f:
            dsl_content = f.read()
    elif not file and dsl:
        dsl_content = dsl
    else:
        click.secho("ERROR: Please choose either --file or --dsl.", fg="bright_red")
        sys.exit()
    client.execute(dsl_content, output_file=output)
