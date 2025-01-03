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
from abc import ABC

from knext.common import rest
from knext.common.env import env


class Client(ABC):
    """
    Base client class.

    This abstract base class is used to derive specific client classes.
    It defines a REST client instance for sending API requests.

    Attributes:
        _rest_client (rest.BaseApi): REST client instance for sending API requests.
    """

    _rest_client: rest.BaseApi

    def __init__(self, host_addr: str = None, project_id: str = None):
        """
        Initialization method to set the connection address and project ID.

        This method checks the provided `host_addr` and `project_id` parameters.
        If these parameters are not provided, it retrieves the values from environment variables.

        Parameters:
            host_addr (str): The address of the component server. If not provided, the value from the environment variable `KAG_PROJECT_HOST_ADDR` is used.
            project_id (int): The ID of the user's project. If not provided, the value from the environment variable `KAG_PROJECT_ID` is used.
        """
        self._host_addr = host_addr or env.host_addr
        self._project_id = project_id or env.id

    @staticmethod
    def serialize(obj):
        """
        Serialize an object for transmission.

        This method uses an instance of rest.ApiClient to sanitize the object,
        making it suitable for serialization into JSON or another format for network transmission.
        Serialization is the process of converting an object into a form that can be transmitted and stored.

        Parameters:
        obj (any): The object to be serialized.

        Returns:
        any: The sanitized object, suitable for serialization and transmission.
        """
        return rest.ApiClient().sanitize_for_serialization(obj)
