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
import logging

from kag.common.llm.openai_client import OpenAIClient
from kag.interface.common.llm_client import LLMClient

logger = logging.getLogger(__name__)

# MiniMax API base URL (OpenAI-compatible)
MINIMAX_DEFAULT_BASE_URL = "https://api.minimax.io/v1"

# MiniMax temperature range: [0.0, 1.0]
MINIMAX_MIN_TEMPERATURE = 0.0
MINIMAX_MAX_TEMPERATURE = 1.0


@LLMClient.register("minimax")
class MiniMaxClient(OpenAIClient):
    """
    A client class for interacting with the MiniMax API.

    MiniMax provides an OpenAI-compatible API endpoint. This client inherits
    from OpenAIClient and adds MiniMax-specific defaults and temperature clamping.

    Supported models:
        - MiniMax-M2.7 (latest, recommended)
        - MiniMax-M2.5
        - MiniMax-M2.5-highspeed (204K context window)

    Configuration example (kag_config.yaml):
        llm:
          type: minimax
          model: MiniMax-M2.7
          api_key: ${MINIMAX_API_KEY}

    Environment variable:
        MINIMAX_API_KEY: API key for MiniMax (auto-detected if api_key is not provided)
    """

    def __init__(
        self,
        model: str = "MiniMax-M2.7",
        api_key: str = None,
        base_url: str = None,
        stream: bool = False,
        temperature: float = 0.7,
        timeout: float = None,
        max_rate: float = 1000,
        time_period: float = 1,
        **kwargs,
    ):
        """
        Initializes the MiniMaxClient instance.

        Args:
            model (str): The MiniMax model to use. Defaults to "MiniMax-M2.7".
            api_key (str): The API key for MiniMax. If not provided, reads from
                           MINIMAX_API_KEY environment variable.
            base_url (str): The API base URL. Defaults to "https://api.minimax.io/v1".
            stream (bool, optional): Whether to stream the response. Defaults to False.
            temperature (float, optional): Sampling temperature. Clamped to [0.0, 1.0].
                                           Defaults to 0.7.
            timeout (float): Timeout for requests. Defaults to None.
        """
        # Auto-detect API key from environment if not provided
        if not api_key:
            api_key = os.environ.get("MINIMAX_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "MiniMax API key is required. Set it via the 'api_key' parameter "
                    "or the MINIMAX_API_KEY environment variable."
                )

        # Use MiniMax default base URL if not provided
        if not base_url:
            base_url = MINIMAX_DEFAULT_BASE_URL

        # Clamp temperature to MiniMax's accepted range [0.0, 1.0]
        original_temperature = temperature
        temperature = max(MINIMAX_MIN_TEMPERATURE, min(MINIMAX_MAX_TEMPERATURE, temperature))
        if temperature != original_temperature:
            logger.warning(
                f"MiniMax temperature clamped from {original_temperature} to {temperature} "
                f"(valid range: [{MINIMAX_MIN_TEMPERATURE}, {MINIMAX_MAX_TEMPERATURE}])"
            )

        super().__init__(
            base_url=base_url,
            model=model,
            api_key=api_key,
            stream=stream,
            temperature=temperature,
            timeout=timeout,
            max_rate=max_rate,
            time_period=time_period,
            **kwargs,
        )
        logger.debug(
            f"Initialize MiniMaxClient with model={model}, base_url={base_url}"
        )
