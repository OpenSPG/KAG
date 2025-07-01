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

import click

from knext.thinker.client import ThinkerClient


@click.option("--subject", help="The subject of reasoning goal, eg: id,type or type")
@click.option("--predicate", help="The predicate of reasoning goal, eg: type")
@click.option("--object", help="The object of reasoning goal, eg: id,type or type")
@click.option("--mode", help="Reasoning mode, eg: spo or node")
@click.option("--params", help="Reasoning context")
def execute_thinker_job(subject="", predicate="", object="", mode="spo", params=""):
    """
    Submit asynchronous reasoner jobs to server by providing DSL file or string.
    """
    client = ThinkerClient()
    client.execute(subject, predicate, object, mode, params)
