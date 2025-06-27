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

from knext.builder import rest
from knext.builder.rest.models.writer_graph_request import WriterGraphRequest
from knext.common.base.client import Client
from knext.common.rest import ApiClient, Configuration


class BuilderClient(Client):
    """ """

    def __init__(self, host_addr: str = None, project_id: int = None):
        super().__init__(host_addr, project_id)
        self._rest_client: rest.BuilderApi = rest.BuilderApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )

    def write_graph(self, sub_graph: dict, operation: str, lead_to_builder: bool):
        request = WriterGraphRequest(
            project_id=self._project_id,
            sub_graph=sub_graph,
            operation=operation,
            enable_lead_to=lead_to_builder,
            token="openspg@8380255d4e49_",
        )
        self._rest_client.builder_job_writer_graph_post(writer_graph_request=request)

    def submit(self, builder_job: dict):
        pass
