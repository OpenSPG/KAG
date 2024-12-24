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

from knext.common.base.client import Client
from knext.common.rest import Configuration, ApiClient
from knext.thinker import rest
from knext.thinker.rest import ThinkerTaskRequest, ThinkerTaskResponse


class ThinkerClient(Client):
    """SPG Thinker Client."""

    def __init__(self, host_addr: str = None, project_id: int = None):
        super().__init__(host_addr, project_id)

        self._rest_client: rest.ThinkerApi = rest.ThinkerApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )

    def execute(self, subject="", predicate="", object="", mode="spo", params=""):
        """
        Execute a synchronous builder job in local runner.
        """
        req: ThinkerTaskRequest = ThinkerTaskRequest(
            project_id=self._project_id,
            subject=subject,
            predicate=predicate,
            object=object,
            mode=mode,
            params=params,
        )
        rep: ThinkerTaskResponse = self._rest_client.reason_thinker_post(
            thinker_task_request=req
        )
        print(rep)


if __name__ == "__main__":
    sc = ThinkerClient("http://127.0.0.1:8887", 2)
    sc.execute(
        subject="DiseaseLevel",
        mode="node",
        params='{"spg.reasoner.thinker.strict":·true,·"收缩压":150}',
    )
