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
from pathlib import Path
import yaml
import click
import knext.project

from knext.schema.marklang.concept_rule_ml import SPGConceptRuleMarkLang
from knext.schema.marklang.schema_ml import SPGSchemaMarkLang
from knext.common.env import env


def commit_schema():
    """
    Commit local schema and generate schema helper.
    """
    schema_file = os.path.join(
        env.project_path,
        knext.project.DEFAULT_SCHEMA_DIR,
        knext.project.DEFAULT_SCHEMA_FILE.replace("$namespace", env.namespace),
    )
    if not Path(schema_file).exists():
        click.secho(f"ERROR: File {schema_file} not exists.", fg="bright_red")
        return

    ml = SPGSchemaMarkLang(schema_file)
    is_altered = ml.sync_schema()

    if is_altered:
        click.secho("Schema is successfully committed.", fg="bright_green")
    else:
        click.secho(
            "There is no diff between local and server-side schema.", fg="bright_yellow"
        )


@click.option("--file", help="Path of DSL file.")
def reg_concept_rule(file):
    """
    Register a concept rule according to DSL file.
    """
    SPGConceptRuleMarkLang(file)
    click.secho(f"Concept rule is successfully registered", fg="bright_green")
