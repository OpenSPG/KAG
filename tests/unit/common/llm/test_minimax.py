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
import asyncio
from unittest.mock import patch, MagicMock

import pytest

from kag.interface import LLMClient


# ---------------------------------------------------------------------------
# Unit tests (no real API calls)
# ---------------------------------------------------------------------------


class TestMiniMaxClientRegistration:
    """Test that MiniMaxClient is properly registered in the LLMClient registry."""

    def test_minimax_type_registered(self):
        """MiniMaxClient should be discoverable via LLMClient.from_config with type='minimax'."""
        assert "minimax" in LLMClient.registry, (
            "Expected 'minimax' to be a registered LLMClient type"
        )

    def test_from_config_creates_minimax_client(self):
        """LLMClient.from_config should create a MiniMaxClient instance."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "model": "MiniMax-M2.7",
                    "enable_check": False,
                }
            )
        assert isinstance(client, MiniMaxClient)

    def test_inherits_openai_client(self):
        """MiniMaxClient should inherit from OpenAIClient."""
        from kag.common.llm.minimax_client import MiniMaxClient
        from kag.common.llm.openai_client import OpenAIClient

        assert issubclass(MiniMaxClient, OpenAIClient)


class TestMiniMaxClientDefaults:
    """Test default values for MiniMaxClient."""

    def test_default_base_url(self):
        """Should use MiniMax API base URL by default."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )
        assert client.base_url == "https://api.minimax.io/v1"

    def test_default_model(self):
        """Should default to MiniMax-M2.7 model."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )
        assert client.model == "MiniMax-M2.7"

    def test_custom_model(self):
        """Should accept custom model name."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "model": "MiniMax-M2.5-highspeed",
                    "enable_check": False,
                }
            )
        assert client.model == "MiniMax-M2.5-highspeed"

    def test_custom_base_url(self):
        """Should accept custom base URL."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "base_url": "https://custom.minimax.io/v1",
                    "enable_check": False,
                }
            )
        assert client.base_url == "https://custom.minimax.io/v1"


class TestMiniMaxClientTemperature:
    """Test temperature clamping behavior."""

    def test_normal_temperature(self):
        """Temperature within [0.0, 1.0] should pass through unchanged."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "temperature": 0.5,
                    "enable_check": False,
                }
            )
        assert client.temperature == 0.5

    def test_temperature_zero(self):
        """Temperature 0.0 should be accepted."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "temperature": 0.0,
                    "enable_check": False,
                }
            )
        assert client.temperature == 0.0

    def test_temperature_one(self):
        """Temperature 1.0 should be accepted."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "temperature": 1.0,
                    "enable_check": False,
                }
            )
        assert client.temperature == 1.0

    def test_temperature_clamped_high(self):
        """Temperature > 1.0 should be clamped to 1.0."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "temperature": 1.5,
                    "enable_check": False,
                }
            )
        assert client.temperature == 1.0

    def test_temperature_clamped_negative(self):
        """Negative temperature should be clamped to 0.0."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "temperature": -0.5,
                    "enable_check": False,
                }
            )
        assert client.temperature == 0.0


class TestMiniMaxClientAPIKey:
    """Test API key handling."""

    def test_api_key_from_parameter(self):
        """Should accept API key directly."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "sk-test-key-123",
                    "enable_check": False,
                }
            )
        assert client.api_key == "sk-test-key-123"

    def test_api_key_from_env(self):
        """Should read API key from MINIMAX_API_KEY environment variable."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "sk-env-key-456"}):
            with patch.object(MiniMaxClient, "check"):
                client = LLMClient.from_config(
                    {
                        "type": "minimax",
                        "enable_check": False,
                    }
                )
            assert client.api_key == "sk-env-key-456"

    def test_missing_api_key_raises(self):
        """Should raise ValueError when no API key is available."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove MINIMAX_API_KEY if it exists
            env = os.environ.copy()
            env.pop("MINIMAX_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="MiniMax API key is required"):
                    LLMClient.from_config(
                        {
                            "type": "minimax",
                            "enable_check": False,
                        }
                    )


class TestMiniMaxClientStreaming:
    """Test streaming configuration."""

    def test_stream_default_false(self):
        """Streaming should default to False."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )
        assert client.stream is False

    def test_stream_enabled(self):
        """Should accept stream=True."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "stream": True,
                    "enable_check": False,
                }
            )
        assert client.stream is True


class TestMiniMaxClientSync:
    """Test synchronous call behavior with mocked API."""

    def test_sync_call(self):
        """Should return text from synchronous call."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from MiniMax!"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            completion_tokens=5, prompt_tokens=10, total_tokens=15
        )
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = client("Hello!")
        assert result == "Hello from MiniMax!"


class TestMiniMaxClientAsync:
    """Test asynchronous call behavior with mocked API."""

    def test_async_call(self):
        """Should return text from asynchronous call."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Async hello from MiniMax!"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage = MagicMock(
            completion_tokens=5, prompt_tokens=10, total_tokens=15
        )

        async def mock_create(**kwargs):
            return mock_response

        client.aclient.chat.completions.create = mock_create

        result = asyncio.run(client.acall("Hello async!"))
        assert result == "Async hello from MiniMax!"


class TestMiniMaxClientToolCalls:
    """Test tool/function calling with mocked API."""

    def test_tool_call_returns_message(self):
        """Should return full message object when tools are used."""
        from kag.common.llm.minimax_client import MiniMaxClient

        with patch.object(MiniMaxClient, "check"):
            client = LLMClient.from_config(
                {
                    "type": "minimax",
                    "api_key": "test-key",
                    "enable_check": False,
                }
            )

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"city": "Beijing"}'

        mock_message = MagicMock()
        mock_message.content = None
        mock_message.tool_calls = [mock_tool_call]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message
        mock_response.usage = MagicMock(
            completion_tokens=5, prompt_tokens=10, total_tokens=15
        )
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]

        result = client("What's the weather in Beijing?", tools=tools)
        assert result.tool_calls[0].function.name == "get_weather"


# ---------------------------------------------------------------------------
# Integration tests (require real API key, skipped by default)
# ---------------------------------------------------------------------------


def _has_minimax_key():
    return bool(os.environ.get("MINIMAX_API_KEY"))


@pytest.mark.skipif(not _has_minimax_key(), reason="MINIMAX_API_KEY not set")
class TestMiniMaxClientIntegration:
    """Integration tests that call the real MiniMax API."""

    def test_sync_call_real(self):
        """Test a real synchronous call to MiniMax API."""
        client = LLMClient.from_config(
            {
                "type": "minimax",
                "model": "MiniMax-M2.7",
                "stream": False,
            }
        )
        result = client("Say 'hello' and nothing else.")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_async_call_real(self):
        """Test a real asynchronous call to MiniMax API."""
        client = LLMClient.from_config(
            {
                "type": "minimax",
                "model": "MiniMax-M2.7",
                "stream": False,
            }
        )
        result = asyncio.run(client.acall("Say 'hello' and nothing else."))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stream_call_real(self):
        """Test a real streaming call to MiniMax API."""
        client = LLMClient.from_config(
            {
                "type": "minimax",
                "model": "MiniMax-M2.7",
                "stream": True,
            }
        )
        result = client("Say 'hello' and nothing else.")
        assert isinstance(result, str)
        assert len(result) > 0
