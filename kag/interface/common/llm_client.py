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
import json
import tempfile
import portalocker

try:
    from json_repair import loads
except:
    from json import loads
from dataclasses import dataclass
from threading import Lock
from typing import Union, Dict, List, Any
import logging
import traceback
import contextvars
from tenacity import retry, stop_after_attempt, wait_exponential
from kag.interface import PromptABC
from kag.common.registry import Registrable
from kag.common.rate_limiter import RATE_LIMITER_MANGER, SYNC_RATE_LIMITER_MANAGER
from kag.common.conf import KAGConstants, KAGConfigAccessor

logger = logging.getLogger(__name__)


@dataclass
class TokenMeter:
    task_id: str = "default-task[0]"
    completion_tokens: int = 0
    prompt_tokens: int = 0
    total_tokens: int = 0
    in_memory: bool = True

    @property
    def ckpt_file(self):
        if self.in_memory:
            return None
        tmp_dir = tempfile.gettempdir()
        path = os.path.join(tmp_dir, f"token-meter-task-{self.task_id}.json")
        return path

    def load(self):
        if self.in_memory:
            return
        if os.path.exists(self.ckpt_file):
            with open(self.ckpt_file, "r") as reader:
                portalocker.lock(reader, portalocker.LOCK_EX)
                data = json.loads(reader.read())
            self.completion_tokens = data["completion_tokens"]
            self.prompt_tokens = data["prompt_tokens"]
            self.total_tokens = data["total_tokens"]

    def dump(self):
        if self.in_memory:
            return
        data = {}

        data["completion_tokens"] = self.completion_tokens
        data["prompt_tokens"] = self.prompt_tokens
        data["total_tokens"] = self.total_tokens
        with open(self.ckpt_file, "w") as writer:
            portalocker.lock(writer, portalocker.LOCK_EX)
            writer.write(json.dumps(data))

    def update(
        self, completion_tokens: int = 0, prompt_tokens: int = 0, total_tokens: int = 0
    ):
        self.load()
        self.completion_tokens += completion_tokens
        self.prompt_tokens += prompt_tokens
        self.total_tokens += total_tokens
        self.dump()

    def to_dict(self):
        self.load()
        return {
            "completion_tokens": self.completion_tokens,
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenMeterFactory:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._meters = {}
            cls._instance._lock = Lock()
        return cls._instance

    def get_meter(self, task_id: str, token_meter_in_memory: bool = True) -> TokenMeter:
        with self._lock:
            if task_id not in self._meters:
                meter = TokenMeter(task_id=task_id, in_memory=token_meter_in_memory)
                self._meters[task_id] = meter
            return self._meters[task_id]

    def remove_meter(self, task_id: str):
        with self._lock:
            if task_id in self._meters:
                ckpt_file = self._meters[task_id].ckpt_file
                try:
                    if os.path.exists(ckpt_file):
                        os.remove(ckpt_file)
                except:
                    pass
                del self._meters[task_id]

    def get_all_meters(self) -> Dict[str, TokenMeter]:
        with self._lock:
            return dict(self._meters)

    def clear_all(self):
        with self._lock:
            self._meters.clear()

    def get_total_usage(self) -> TokenMeter:
        with self._lock:
            total = TokenMeter()
            for meter in self._meters.values():
                total += meter
            return total


CURRENT_TASK_ID = contextvars.ContextVar("current_task_id", default="default-task[0]")
TOKEN_METER_IN_MEMORY = contextvars.ContextVar("token_meter_in_memory", default=True)


class LLMCallCcontext:
    def __init__(self, task_id, token_meter_in_memory):
        self.task_id = task_id
        self.token_meter_in_memory = token_meter_in_memory
        self.task_id_token = None
        self.token_meter_in_memory_token = None

    def __enter__(self):
        self.task_id_token = CURRENT_TASK_ID.set(self.task_id)
        self.token_meter_in_memory_token = TOKEN_METER_IN_MEMORY.set(
            self.token_meter_in_memory
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        CURRENT_TASK_ID.reset(self.task_id_token)
        TOKEN_METER_IN_MEMORY.reset(self.token_meter_in_memory_token)


class LLMClient(Registrable):
    """
    A class that provides methods for performing inference using large language model.

    This class includes methods to call the model with a prompt, parse the response, and handle batch processing of prompts.
    """

    def __init__(
        self, name: str = "", max_rate: float = 1000, time_period: float = 1, **kwargs
    ):
        super().__init__(**kwargs)
        self.limiter = RATE_LIMITER_MANGER.get_rate_limiter(name, max_rate, time_period)
        self.sync_limiter = SYNC_RATE_LIMITER_MANAGER.get_rate_limiter(
            name, max_rate, time_period
        )
        self.enable_check = kwargs.get("enable_check", True)
        self.max_tokens = kwargs.get("max_tokens", 8192)
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def __call__(self, prompt: Union[str, dict, list], **kwargs) -> str:
        """
        Perform inference on the given prompt and return the result.

        Args:
            prompt (Union[str, dict, list]): Input prompt for inference.

        Returns:
            str: Inference result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        raise NotImplementedError

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def acall(self, prompt: Union[str, dict, list], **kwargs) -> str:
        """
        Perform inference on the given prompt and return the result asynchronously.

        Args:
            prompt (Union[str, dict, list]): Input prompt for inference.

        Returns:
            str: Inference result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        return self(prompt, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def call_with_json_parse(self, prompt: Union[str, dict, list], **kwargs):
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        Args:
            prompt (Union[str, dict, list]): Input prompt for inference.

        Returns:
            Any: Parsed result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        res = self(prompt, **kwargs)
        _end = res.rfind("```")
        _start = res.find("```json")
        if _end != -1 and _start != -1:
            if _end == _start:
                logger.error(
                    f"response is not intact, please set max_tokens. res={res}"
                )
                return res
            json_str = res[_start + len("```json") : _end].strip()
        else:
            json_str = res
        try:
            json_result = loads(json_str)
        except Exception as e:
            logger.info(f"parse json failed {json_str}, info: {e}")
            return res
        return json_result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def acall_with_json_parse(self, prompt: Union[str, dict, list], **kwargs):
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        Args:
            prompt (Union[str, dict, list]): Input prompt for inference.

        Returns:
            Any: Parsed result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        res = await self.acall(prompt, **kwargs)
        _end = res.rfind("```")
        _start = res.find("```json")
        if _end != -1 and _start != -1:
            if _end == _start:
                logger.error(
                    f"response is not intact, please set max_tokens. res={res}"
                )
                return res
            json_str = res[_start + len("```json") : _end].strip()
        else:
            json_str = res
        try:
            json_result = loads(json_str)
            if not json_result:
                return res
        except:
            return res
        return json_result

    def invoke(
        self,
        variables: Dict[str, Any],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
        with_except: bool = True,
        **kwargs,
    ):
        """
        Call the model and process the result.

        Args:
            variables (Dict[str, Any]): Variables used to build the prompt.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.
            with_except (bool, optional): Whether to raise an exception if an error occurs. Defaults to False.

        Returns:
            List: Processed result list.
        """
        result = []
        prompt = prompt_op.build_prompt(variables)
        if isinstance(prompt, list):
            prompt = ""
            kwargs["messages"] = prompt
        logger.debug(f"Prompt: {prompt}")
        if not prompt:
            return result
        response = ""
        tools = kwargs.get("tools", None)
        if tools:
            with_json_parse = False
        try:
            self.sync_limiter.acquire()
            response = (
                self.call_with_json_parse(prompt=prompt, **kwargs)
                if with_json_parse
                else self(prompt, **kwargs)
            )
            if tools:
                return response
            result = prompt_op.parse_response(response, model=self.model, **variables)
            logger.debug(f"Result: {result}")
            return result
        except Exception as e:
            import traceback

            logger.info(
                f"Error {e} during invocation: {traceback.format_exc()}. prompt={prompt} response={response}"
            )
            if with_except:
                raise RuntimeError(
                    f"LLM invoke exception, info: {e}\nllm input: \n{prompt}\nllm output: \n{response}"
                )

    async def ainvoke(
        self,
        variables: Dict[str, Any],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
        with_except: bool = True,
        **kwargs,
    ):
        """
        Call the model and process the result.

        Args:
            **kwargs:
            variables (Dict[str, Any]): Variables used to build the prompt.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.
            with_except (bool, optional): Whether to raise an exception if an error occurs. Defaults to False.
        Returns:
            List: Processed result list.
        """
        result = []
        prompt = prompt_op.build_prompt(variables)
        # logger.info(f"Prompt: {prompt}")
        if not prompt:
            return result
        if isinstance(prompt, list):
            prompt = ""
            kwargs["messages"] = prompt

        response = ""
        tools = kwargs.get("tools", None)
        if tools:
            with_json_parse = False

        async with self.limiter:
            try:
                response = await (
                    self.acall_with_json_parse(prompt=prompt, **kwargs)
                    if with_json_parse
                    else self.acall(prompt, **kwargs)
                )
                if tools:
                    return response
                else:
                    result = prompt_op.parse_response(
                        response, model=self.model, **variables
                    )
                    logger.debug(f"Result: {result}")
            except Exception as e:
                import traceback

                logger.info(
                    f"Error {e} during invocation: {traceback.format_exc()} prompt={prompt} response={response}"
                )
                if with_except:
                    raise RuntimeError(
                        f"LLM invoke exception, info: {e}\nllm input: \n{prompt}\nllm output: \n{response}"
                    )
        return result

    def batch(
        self,
        variables: Dict[str, Any],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
    ) -> List:
        """
        Batch process prompts.

        Args:
            variables (Dict[str, Any]): Variables used to build the prompts.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.

        Returns:
            List: List of all processed results.
        """
        results = []
        prompts = prompt_op.build_prompt(variables)
        # If there is only one prompt, call the `invoke` method directly
        if isinstance(prompts, str):
            return self.invoke(variables, prompt_op, with_json_parse=with_json_parse)

        for idx, prompt in enumerate(prompts, start=0):
            response = ""
            logger.debug(f"Prompt_{idx}: {prompt}")
            try:
                response = (
                    self.call_with_json_parse(prompt=prompt)
                    if with_json_parse
                    else self(prompt)
                )
                logger.debug(f"Response_{idx}: {response}")
                result = prompt_op.parse_response(
                    response, idx=idx, model=self.model, **variables
                )
                logger.debug(f"Result_{idx}: {result}")
                results.extend(result)
            except Exception as e:
                logger.error(f"Error processing prompt {idx}: {e}. response={response}")
                logger.debug(traceback.format_exc())
                continue
        return results

    async def abatch(
        self,
        variables: Dict[str, Any],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
    ) -> List:
        """
        Batch process prompts.

        Args:
            variables (Dict[str, Any]): Variables used to build the prompts.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.

        Returns:
            List: List of all processed results.
        """
        results = []
        prompts = prompt_op.build_prompt(variables)
        # If there is only one prompt, call the `invoke` method directly
        if isinstance(prompts, str):
            return self.invoke(variables, prompt_op, with_json_parse=with_json_parse)

        for idx, prompt in enumerate(prompts, start=0):
            logger.debug(f"Prompt_{idx}: {prompt}")
            async with self.limiter:
                try:
                    response = await (
                        self.acall_with_json_parse(prompt=prompt)
                        if with_json_parse
                        else self.acall(prompt)
                    )
                    logger.debug(f"Response_{idx}: {response}")
                    result = prompt_op.parse_response(
                        response, idx=idx, model=self.model, **variables
                    )
                    logger.debug(f"Result_{idx}: {result}")
                    results.extend(result)
                except Exception as e:
                    logger.error(f"Error processing prompt {idx}: {e}")
                    logger.debug(traceback.format_exc())
                    continue
        return results

    def check(self):
        if not self.enable_check:
            return

        if (
            hasattr(self.kag_project_config, "llm_config_check")
            and self.kag_project_config.llm_config_check
        ):
            try:
                self.__call__("Are you OK?")
            except Exception as e:
                logger.error("LLM config check failed!")
                raise e

    @staticmethod
    def get_token_meter():
        task_id = CURRENT_TASK_ID.get()
        token_meter_in_memory = TOKEN_METER_IN_MEMORY.get()

        return TokenMeterFactory().get_meter(task_id, token_meter_in_memory)
