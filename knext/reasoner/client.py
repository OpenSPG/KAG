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
import datetime
from knext.reasoner.rest.models.reason_task_response import ReasonTaskResponse

import knext.common.cache
from knext.common.base.client import Client
from knext.common.rest import ApiClient, Configuration
from knext.reasoner import ReasonTask
from knext.reasoner import rest
from knext.reasoner.rest import SpgTypeQueryRequest
from knext.schema.client import SchemaSession
from knext.schema.model.base import SpgTypeEnum

reason_cache = knext.common.cache.SchemaCache()


class ReasonerClient(Client):
    """SPG Reasoner Client."""

    def __init__(self, host_addr: str = None, project_id: int = None, namespace=None):
        super().__init__(host_addr, str(project_id))
        self._rest_client: rest.ReasonerApi = rest.ReasonerApi(
            api_client=ApiClient(configuration=Configuration(host=host_addr))
        )
        self._namespace = namespace or os.environ.get("KAG_PROJECT_NAMESPACE")
        self._session = None
        # load schema cache
        self.get_reason_schema()

    def create_session(self):
        """Create session for altering schema."""
        schema_session = reason_cache.get(self._project_id)
        if not schema_session:
            schema_session = SchemaSession(self._rest_client, self._project_id)
            reason_cache.put(self._project_id, schema_session)
        return schema_session

    def get_reason_schema(self):
        """
        Create a new session and load schema information.

        - Create a session object `schema_session`.
        - Iterate through all types in the session and filter out types that are Concepts, Entities, or Events.
        - Construct a dictionary where keys are type names and values are the type objects themselves.
        - Return the constructed dictionary `schema`.
        """
        schema_session = self.create_session()
        schema = {
            k: v
            for k, v in schema_session.spg_types.items()
            if v.spg_type_enum
            in [SpgTypeEnum.Concept, SpgTypeEnum.Entity, SpgTypeEnum.Event]
        }
        return schema

    def generate_graph_connect_config(self, lib):
        """
        Generates the graph connection configuration based on environment variables.

        This function first attempts to retrieve the graph store URI from environment variables.
        If the URI is not set, it returns the local graph store URL and the local graph state class.
        If the URI is set, it retrieves the username, password, and database information from
        environment variables and constructs a graph store URL with this information.

        Parameters:
        lib (reasoner constants): Contains constants and classes related to graph connections.

        Returns:
        tuple: A tuple containing the graph store URL and the graph state class. If the URI is from
               environment variables, the URL is a remote address; otherwise, it is a local address.
        """
        # Attempt to get the graph store URI; if not set, default to an empty string
        uri = os.environ.get("KAG_GRAPH_STORE_URI", "")
        # If URI is empty, return the local graph store URL and the local graph state class
        if uri == "":
            return lib.LOCAL_GRAPH_STORE_URL, lib.LOCAL_GRAPH_STATE_CLASS

        # Retrieve username, password, and database information from environment variables
        user = os.getenv("KAG_GRAPH_STORE_USER")
        password = os.getenv("KAG_GRAPH_STORE_PASSWORD")
        database = os.getenv("KAG_GRAPH_STORE_DATABASE")
        namespace = self._namespace or os.environ.get("KAG_PROJECT_NAMESPACE")
        # Construct a graph store URL with authentication information
        graph_store_url = f"{uri}?user={user}&password={password}&database={database}&namespace={namespace}"

        # Return the constructed graph store URL and the local graph state class
        return graph_store_url, lib.LOCAL_GRAPH_STATE_CLASS

    def execute(self, dsl_content: str, output_file: str = None):
        """
        Execute a synchronous builder job in local runner.
        """
        task_response: ReasonTaskResponse = self.syn_execute(dsl_content)
        task: ReasonTask = task_response.task
        if task.status != "FINISH":
            print(f"RUN {task.status} {dsl_content}")
        else:
            default_output_file = output_file or (
                f"./{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            )
            show_data = [
                task.result_table_result.header
            ] + task.result_table_result.rows
            import pandas as pd

            df = pd.DataFrame(show_data)
            print(df)
            df.to_csv(default_output_file, index=False)

    def query_node(self, label, id_value):
        req = SpgTypeQueryRequest(
            project_id=self._project_id, spg_type=label, ids=[id_value]
        )
        resp = self._rest_client.query_spg_type_post(spg_type_query_request=req)
        if len(resp) == 0:
            return {}
        return resp[0].properties

    def syn_execute(self, dsl_content: str, **kwargs):
        task = ReasonTask(project_id=self._project_id, dsl=dsl_content, params=kwargs)
        return self._rest_client.reason_run_post(reason_task=task)


if __name__ == "__main__":
    sc = ReasonerClient("http://127.0.0.1:8887", 4)
    reason_schema = sc.get_reason_schema()
    print(reason_schema)
    prop_set = sc.query_node("KQA.Others", "Panic_disorder")
    import time

    start_time = time.time()
    ret = sc.syn_execute(
        "MATCH (n:KQA.Others)-[p:rdf_expand()]-(o:Entity) WHERE n.id in $nid and o.id in $oid RETURN p",
        start_alias="n",
        nid='["Panic_disorder"]',
        oid='["Anxiety_and_nervousness"]',
    )
    print(ret)
    print(f"cost={time.time() - start_time}")
