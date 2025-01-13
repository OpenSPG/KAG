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

# from knext.command.sub_command.builder import execute
from knext.command.sub_command.project import (
    create_project,
    restore_project,
    update_project,
    list_project,
)
from knext.command.sub_command.reasoner import execute_reasoner_job
from knext.command.sub_command.schema import commit_schema
from knext.command.sub_command.schema import reg_concept_rule
from knext.command.exception import _ApiExceptionHandler
from knext import __version__
from knext.command.sub_command.thinker import execute_thinker_job


@click.group(cls=_ApiExceptionHandler)
@click.version_option(__version__)
def _main() -> None:
    pass


# @_main.group()
# def builder() -> None:
#     """Builder client."""
#     pass
#
#
# builder.command("execute")(execute)


@_main.group()
def project() -> None:
    """Project client."""
    pass


project.command("create")(create_project)
project.command("restore")(restore_project)
project.command("update")(update_project)
project.command("list")(list_project)


@_main.group()
def schema() -> None:
    """Schema client."""
    pass


schema.command("commit")(commit_schema)
schema.command("reg_concept_rule")(reg_concept_rule)


@_main.group()
def reasoner() -> None:
    """Reasoner client."""
    pass


reasoner.command("execute")(execute_reasoner_job)


@_main.group()
def thinker() -> None:
    """Thinker client."""
    pass


thinker.command("execute")(execute_thinker_job)

if __name__ == "__main__":
    _main()
