# -*- coding: utf-8 -*-
from re import sub
import pytest
import asyncio
from kag.interface import LLMClient


def get_openai_config():
    return {
        "type": "openai",
        "base_url": "https://api.siliconflow.cn/v1/",
        "api_key": "sk-",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "stream": False,
    }


def get_ollama_config():
    return {
        "type": "ollama",
        "model": "qwen2.5:0.5b",
        "stream": False,
    }


# @pytest.mark.skip(reason="Missing API key")
def test_llm_client():

    print("stream = False")
    for conf in [get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        rsp = client("Who are you?")
        print(f"rsp = {rsp}")
    print("stream = True")
    for conf in [get_openai_config(), get_ollama_config()]:
        conf["stream"] = True
        client = LLMClient.from_config(conf)
        rsp = client("Who are you?")
        print(f"rsp = {rsp}")


async def call_llm_client_async():

    print("stream = False")
    tasks = []
    for conf in [get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        task = asyncio.create_task(client.acall("Who are you?"))
        tasks.append(task)
    result = await asyncio.gather(*tasks)
    for rsp in result:
        print(f"rsp = {rsp}")

    print("stream = True")
    tasks = []
    for conf in [get_openai_config(), get_ollama_config()]:
        conf["stream"] = True
        client = LLMClient.from_config(conf)
        task = asyncio.create_task(client.acall("Who are you?"))
        tasks.append(task)
    result = await asyncio.gather(*tasks)
    for rsp in result:
        print(f"rsp = {rsp}")

    return result


# @pytest.mark.skip(reason="Missing API key")
def test_llm_client_async():
    res = asyncio.run(call_llm_client_async())
    return res


def test_mock_llm_client():
    conf = {"type": "mock"}
    client = LLMClient.from_config(conf)
    rsp = client.call_with_json_parse("who are you?")
    assert rsp == "I am an intelligent assistant"


def test_llm_client_with_func_call():
    for conf in [get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        subtract_two_numbers_tool = {
            "type": "function",
            "function": {
                "name": "subtract_two_numbers",
                "description": "Subtract two numbers",
                "parameters": {
                    "type": "object",
                    "required": ["a", "b"],
                    "properties": {
                        "a": {"type": "integer", "description": "The first number"},
                        "b": {"type": "integer", "description": "The second number"},
                    },
                },
            },
        }

        tool_calls = client(
            "What is three subtract one?", tools=[subtract_two_numbers_tool]
        )
        print(f"tool_calls = {tool_calls}")


async def call_llm_client_with_func_call_async():
    for conf in [get_openai_config(), get_ollama_config()]:
        client = LLMClient.from_config(conf)
        subtract_two_numbers_tool = {
            "type": "function",
            "function": {
                "name": "subtract_two_numbers",
                "description": "Subtract two numbers",
                "parameters": {
                    "type": "object",
                    "required": ["a", "b"],
                    "properties": {
                        "a": {"type": "integer", "description": "The first number"},
                        "b": {"type": "integer", "description": "The second number"},
                    },
                },
            },
        }

        tool_calls = await client.acall(
            "What is three subtract one? ",
            tools=[subtract_two_numbers_tool],
        )
        print(f"tool_calls = {tool_calls}")


def test_llm_client_with_func_call_async():
    res = asyncio.run(call_llm_client_with_func_call_async())
    return res
