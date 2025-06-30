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
import click
import knext.project
from kag.indexer import KAGIndexManager

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

    if Path(schema_file).exists():
        ml = SPGSchemaMarkLang(
            schema_file, host_addr=env.host_addr, project_id=env.project_id
        )
    else:
        ml = None
    index_managers = KAGIndexManager.list_available()
    index_ml = None
    for index_manager_name in index_managers:
        config = {
            "type": index_manager_name,
            "llm_config": None,
            "vectorize_model_config": None,
        }

        index_mgr = KAGIndexManager.from_config(config)
        schema_str = index_mgr.schema
        if not schema_str:
            continue
        schema_str = f"namespace {env.namespace}\n" + schema_str
        cur_index_ml = SPGSchemaMarkLang(
            filename="",
            script_data_str=schema_str,
            host_addr=env.host_addr,
            project_id=env.project_id,
        )
        if index_ml is None:
            index_ml = cur_index_ml
        else:
            index_ml.types.update(cur_index_ml.types)

    if ml is None and index_ml is None:
        click.secho(f"ERROR: File {schema_file} and index not exists.", fg="bright_red")
        return
    if ml is None:
        ml = index_ml
    elif index_ml is not None:
        ml.types.update(index_ml.types)

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
    SPGConceptRuleMarkLang(file, host_addr=env.host_addr, project_id=env.project_id)
    click.secho(f"Concept rule is successfully registered", fg="bright_green")
