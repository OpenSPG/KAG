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
    with open(os.path.join(PWD, "resource/cfg.tmpl"), "r") as reader:
        template = reader.read()
    with open(os.path.join(PWD, "resource/cfg"), "r") as reader:
        rendered = reader.read()
    return template, rendered


def set_render_contents(template_content, rendered_content):
    with open(os.path.join(PWD, "resource/cfg.tmpl"), "w") as writer:
        writer.write(template_content)
    with open(os.path.join(PWD, "resource/cfg"), "w") as writer:
        writer.write(rendered_content)


def _test_render_template(rendered_content):
    work_dir = os.path.join(PWD, "resource")
    render_template(
        root=work_dir,
        file="cfg.tmpl",
        project_name="TEST",
        description="TEST",
        namespace="kag",
        project_id="0324",
        project_dir="/root",
    )
    rendered_file = os.path.join(work_dir, "cfg")
    with open(rendered_file, "r") as reader:
        rendered = reader.read()
    assert rendered_content == rendered, "template render error"


def test_render_template():
    template_content, rendered_content = get_render_contents()
    try:
        _test_render_template(rendered_content)
    except Exception as e:
        set_render_contents(template_content, rendered_content)
        raise e
    set_render_contents(template_content, rendered_content)


test_render_template()
