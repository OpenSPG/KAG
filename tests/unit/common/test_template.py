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
from kag.common.utils import render_template

PWD = os.path.dirname(__file__)


def get_render_contents():
    with open(os.path.join(PWD, "data/cfg.yaml.tmpl"), "r") as reader:
        template = reader.read()
    with open(os.path.join(PWD, "data/cfg.yaml"), "r") as reader:
        rendered = reader.read()
    return template, rendered


def set_render_contents(template_content, rendered_content):
    with open(os.path.join(PWD, "data/cfg.yaml.tmpl"), "w") as writer:
        writer.write(template_content)
    with open(os.path.join(PWD, "data/cfg.yaml"), "w") as writer:
        writer.write(rendered_content)


def _test_render_template(rendered_content):
    work_dir = os.path.join(PWD, "data")

    data = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "secret",
            "name": "my_database",
        },
        "server": {"host": "0.0.0.0", "port": 8080},
    }

    render_template(root_dir=work_dir, file="cfg.yaml.tmpl", **data)
    rendered_file = os.path.join(work_dir, "cfg.yaml")
    with open(rendered_file, "r") as reader:
        rendered = reader.read()
    assert (
        rendered_content.strip() == rendered.strip()
    ), f"\n{rendered_content}\n=====VS=======\n{rendered}"


def test_render_template():
    template_content, rendered_content = get_render_contents()
    try:
        _test_render_template(rendered_content)
    except Exception as e:
        set_render_contents(template_content, rendered_content)
        raise e
    set_render_contents(template_content, rendered_content)
