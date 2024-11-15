# -*- coding: utf-8 -*-
import pytest
from kag.interface import LLMClient


def get_vllm_config():
    return {
        "type": "vllm",
        "model": "qwen2.5-3b",
        "base_url": "http://localhost:8000/v1/chat/completions",
    }


def get_openai_config():
    return {
        "type": "openai",
        "base_url": "https://api.deepseek.com/beta",
        "api_key": "",
        "model": "deepseek-chat",
    }


def get_ollama_config():
    return {
        "type": "ollama",
        "base_url": "http://localhost:11434/api/generate",
        "model": "llama3.1",
    }


@pytest.mark.skip(reason="Missing API key")
def test_llm_client():

    for conf in [get_vllm_config(), get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        rsp = client("Who are you?")
        # assert rsp is not None


def test_mock_llm_client():
    conf = {"type": "mock"}
    client = LLMClient.from_config(conf)
    rsp = client.call_with_json_parse("who are you?")
    assert rsp == "I am an intelligent assistant"
