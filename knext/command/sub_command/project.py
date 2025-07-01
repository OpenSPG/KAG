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
from collections import OrderedDict
import logging
import re
import json
import os
import sys
from configparser import ConfigParser
from pathlib import Path
from ruamel.yaml import YAML
from typing import Optional

import click

from knext.common.utils import copytree, copyfile
from knext.project.client import ProjectClient

from knext.common.env import env, DEFAULT_HOST_ADDR

from kag.common.llm.llm_config_checker import LLMConfigChecker
from kag.common.vectorize_model.vectorize_model_config_checker import (
    VectorizeModelConfigChecker,
)
from shutil import copy2

try:
    import kag_ant
except ImportError:
    pass

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)

logger = logging.getLogger(__name__)


def _render_template(namespace: str, tmpl: str, **kwargs):
    config_path = kwargs.get("config_path", None)
    project_dir = Path(namespace)
    if not project_dir.exists():
        project_dir.mkdir()

    import kag.templates.project

    src = Path(kag.templates.project.__path__[0])
    copytree(
        src,
        project_dir.resolve(),
        namespace=namespace,
        root=namespace,
        tmpl=tmpl,
        **kwargs,
    )

    import kag.templates.schema

    src = Path(kag.templates.schema.__path__[0]) / f"{{{{{tmpl}}}}}.schema.tmpl"
    if not src.exists():
        click.secho(
            f"ERROR: No such schema template: {tmpl}.schema.tmpl",
            fg="bright_red",
        )
    dst = project_dir.resolve() / "schema" / f"{{{{{tmpl}}}}}.schema.tmpl"
    copyfile(src, dst, namespace=namespace, **{tmpl: namespace})

    tmpls = [tmpl, "default"] if tmpl != "default" else [tmpl]
    # find all .yaml files in project dir
    config = yaml.load(Path(config_path).read_text() or "{}")
    project_id = kwargs.get("id", None)
    config["project"]["id"] = project_id
    config_file_path = project_dir.resolve() / "kag_config.yaml"
    with open(config_file_path, "w", encoding="utf-8", newline="\n") as config_file:
        yaml.dump(config, config_file)
    return project_dir


def _recover_project(prj_path: str):
    """
    Recover project by a project dir path.
    """
    if not Path(prj_path).exists():
        click.secho(f"ERROR: No such directory: {prj_path}", fg="bright_red")
        sys.exit()

    project_name = env.project_config.get("namespace", None)
    namespace = env.project_config.get("namespace", None)
    desc = env.project_config.get("description", None)
    if not namespace:
        click.secho(
            f"ERROR: No project namespace found in {env.config_path}.",
            fg="bright_red",
        )
        sys.exit()
    client = ProjectClient(host_addr=env.host_addr, project_id=env.project_id)
    project = client.get(namespace=namespace) or client.create(
        name=project_name,
        desc=desc,
        namespace=namespace,
        config=env._config,
        visibility=env.project_config.get("visibility", "PRIVATE"),
        tag=env.project_config.get("tag", "LOCAL"),
        userNo=env.project_config.get("userNo", "openspg"),
    )

    env._config["project"]["id"] = project.id
    env.dump()

    click.secho(
        f"Project [{project_name}] with namespace [{namespace}] was successfully recovered from [{prj_path}].",
        fg="bright_green",
    )


@click.option("--config_path", help="Path of config.", required=True)
@click.option(
    "--tmpl",
    help="Template of project, use default if not specified.",
    default="default",
    type=click.Choice(["default", "medical"], case_sensitive=False),
)
@click.option(
    "--delete_cfg",
    help="whether delete your defined .yaml file.",
    default=False,
    hidden=True,
)
def create_project(
    config_path: str, tmpl: Optional[str] = None, delete_cfg: bool = False
):
    """
    Create new project with a demo case.
    """

    config = yaml.load(Path(config_path).read_text() or "{}")
    project_config = config.get("project", {})
    namespace = project_config.get("namespace", None)
    name = project_config.get("namespace", None)
    host_addr = project_config.get("host_addr", None)

    if not namespace:
        click.secho("ERROR: namespace is required.")
        sys.exit()

    if not re.match(r"^[A-Z][A-Za-z0-9]{0,15}$", namespace):
        raise click.BadParameter(
            f"Invalid namespace: {namespace}."
            f" Must start with an uppercase letter, only contain letters and numbers, and have a maximum length of 16."
        )

    if not tmpl:
        tmpl = "default"

    project_id = None

    llm_config_checker = LLMConfigChecker()
    vectorize_model_config_checker = VectorizeModelConfigChecker()
    llm_config = config.get("chat_llm", {})
    vectorize_model_config = config.get("vectorizer", {})
    try:
        llm_config_checker.check(json.dumps(llm_config))
        dim = vectorize_model_config_checker.check(json.dumps(vectorize_model_config))
        config["vectorizer"]["vector_dimensions"] = dim
    except Exception as e:
        click.secho(f"Error: {e}", fg="bright_red")
        sys.exit()

    if host_addr:
        client = ProjectClient(host_addr=host_addr)
        project = client.create(
            name=name,
            namespace=namespace,
            config=config,
            visibility=env.project_config.get("visibility", "PRIVATE"),
            tag=env.project_config.get("tag", "LOCAL"),
            userNo=env.project_config.get("userNo", "openspg"),
        )

        if project and project.id:
            project_id = project.id
    else:
        click.secho("ERROR: host_addr is required.", fg="bright_red")
        sys.exit()

    project_dir = _render_template(
        namespace=namespace,
        tmpl=tmpl,
        id=project_id,
        with_server=(host_addr is not None),
        host_addr=host_addr,
        name=name,
        config_path=config_path,
        delete_cfg=delete_cfg,
    )

    current_dir = os.getcwd()
    os.chdir(project_dir)
    update_project(project_dir)
    os.chdir(current_dir)

    if delete_cfg and os.path.exists(config_path):
        os.remove(config_path)

    click.secho(
        f"Project with namespace [{namespace}] was successfully created in {project_dir.resolve()} \n"
        + "You can checkout your project with: \n"
        + f"  cd {project_dir}",
        fg="bright_green",
    )


@click.option("--host_addr", help="Address of spg server.", default=None)
@click.option("--proj_path", help="Path of project.", default=None)
def restore_project(host_addr, proj_path):
    if host_addr is None:
        host_addr = env.host_addr
    if proj_path is None:
        proj_path = env.project_path
    proj_client = ProjectClient(host_addr=host_addr)

    project_wanted = proj_client.get_by_namespace(namespace=env.namespace)
    if not project_wanted:
        if host_addr:
            client = ProjectClient(host_addr=host_addr)
            project = client.create(
                name=env.name,
                namespace=env.namespace,
                config=env._config,
                visibility=env.project_config.get("visibility", "PRIVATE"),
                tag=env.project_config.get("tag", "LOCAL"),
                userNo=env.project_config.get("userNo", "openspg"),
            )
            project_id = project.id
    else:
        project_id = project_wanted.id
    # write project id and host addr to kag_config.yaml
    env._config["project"]["id"] = project_id
    env._config["project"]["host_addr"] = host_addr
    env.dump()
    if proj_path:
        _recover_project(proj_path)
        update_project(proj_path)


@click.option("--proj_path", help="Path of config.", default=None)
def update_project(proj_path):
    if not proj_path:
        proj_path = env.project_path
    client = ProjectClient(host_addr=env.host_addr)

    llm_config_checker = LLMConfigChecker()
    vectorize_model_config_checker = VectorizeModelConfigChecker()
    llm_config = env.config.get("chat_llm", {})
    vectorize_model_config = env.config.get("vectorizer", {})
    try:
        llm_config_checker.check(json.dumps(llm_config))
        dim = vectorize_model_config_checker.check(json.dumps(vectorize_model_config))
        env._config["vectorizer"]["vector_dimensions"] = dim
    except Exception as e:
        click.secho(f"Error: {e}", fg="bright_red")
        sys.exit()

    logger.info(f"project id: {env.id}")
    client.update(
        id=env.id,
        namespace=env.namespace,
        config=env._config,
        visibility=env.project_config.get("visibility", "PRIVATE"),
        tag=env.project_config.get("tag", "LOCAL"),
        userNo=env.project_config.get("userNo", "openspg"),
    )
    click.secho(
        f"Project [{env.name}] with namespace [{env.namespace}] was successfully updated from [{proj_path}].",
        fg="bright_green",
    )


@click.option("--host_addr", help="Address of spg server.", default=DEFAULT_HOST_ADDR)
def list_project(host_addr):
    client = ProjectClient(host_addr=host_addr)
    projects = client.get_all()

    headers = ["Project Name", "Project ID"]

    click.echo(click.style(f"{' | '.join(headers)}", fg="bright_green", bold=True))
    click.echo(
        click.style(
            f"{'-' * (len(headers[0]) + len(headers[1]) + 3)}", fg="bright_green"
        )
    )

    for project_name, project_id in projects.items():
        click.echo(
            click.style(f"{project_name:<20} | {project_id:<10}", fg="bright_green")
        )
