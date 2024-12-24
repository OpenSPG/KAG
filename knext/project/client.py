# coding: utf-8
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
import json
import os

from knext.common.base.client import Client
from knext.common.rest import Configuration, ApiClient
from knext.project import rest


class ProjectClient(Client):
    """ """

    def __init__(self, host_addr: str = None, project_id: int = None):
        super().__init__(host_addr, project_id)
        self._rest_client: rest.ProjectApi = rest.ProjectApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )

    def get_config(self, project_id: str):
        project = self.get(id=int(project_id or os.getenv("KAG_PROJECT_ID")))
        if not project:
            return {}
        config = project.config
        config = json.loads(config) if config else {}
        return config

    def get(self, **conditions):
        projects = self._rest_client.project_get()
        for project in projects:
            condition = True
            for k, v in conditions.items():
                condition = condition and str(getattr(project, k)) == str(v)
            if condition:
                return project
        return None

    def get_by_namespace(self, namespace: str):
        projects = self._rest_client.project_get()
        for project in projects:
            if str(project.namespace) == str(namespace):
                return project
        return None

    def create(self, name: str, namespace: str, desc: str = None, auto_schema=False):
        project_create_request = rest.ProjectCreateRequest(
            name=name, desc=desc, namespace=namespace, auto_schema=auto_schema
        )

        project = self._rest_client.project_create_post(
            project_create_request=project_create_request
        )
        return project

    def update(self, id, config):
        project_create_request = rest.ProjectCreateRequest(id=id, config=config)
        project = self._rest_client.update_post(
            project_create_request=project_create_request
        )
        return project

    def get_all(self):
        project_list = {}
        projects = self._rest_client.project_get()
        for project in projects:
            project_list[project.namespace] = project.id
        return project_list
