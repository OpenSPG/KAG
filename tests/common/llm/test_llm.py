# -*- coding: utf-8 -*-
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


def test_llm_client():

    for conf in [get_vllm_config(), get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        rsp = client("Who are you?")
        # assert rsp is not None
