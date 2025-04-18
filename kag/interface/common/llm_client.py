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
try:
    from json_repair import loads
except:
    from json import loads
import io
import os
from typing import Union, Dict, Any, List
import logging
import asyncio
import requests
import tarfile
from tenacity import retry, stop_after_attempt, wait_exponential
from kag.interface import PromptABC
from kag.common.registry import Registrable
from kag.common.rate_limiter import RATE_LIMITER_MANGER

logger = logging.getLogger(__name__)


class LLMClient(Registrable):
    """
    A class that provides methods for performing inference using large language model.

    This class includes methods to call the model with a prompt, parse the response, and handle batch processing of prompts.
    """

    def __init__(
        self, name: str, max_rate: float = 1000, time_period: float = 1, **kwargs
    ):
        super().__init__(**kwargs)
        self.limiter = RATE_LIMITER_MANGER.get_rate_limiter(name, max_rate, time_period)
        self.enable_check = kwargs.get("enable_check", True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def __call__(
        self, prompt: Union[str, List[str], List[Dict], List[List[Dict]]], **kwargs
    ) -> Union[str, List[str]]:
        """
        Perform inference on the given prompt and return the result.

        Args:
            prompt (Union[str, List[str], List[Dict], List[List[Dict]]]): Input prompt
                with raw string or OpenAI-style message format.

        Returns:
            str: Inference result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        raise NotImplementedError

    def _download_model(self, path, url):
        """
        Downloads a model from a specified URL and extracts it to a given path.

        Args:
            path (str): The directory path to save the downloaded model.
            url (str): The URL from which to download the model.

        Raises:
            RuntimeError: If the model configuration file is not found at the specified path.
        """
        logger.info(f"download model from:\n{url} to:\n{path}")
        res = requests.get(url)
        with io.BytesIO(res.content) as fileobj:
            with tarfile.open(fileobj=fileobj) as tar:
                tar.extractall(path=path)
        config_path = os.path.join(path, "config.json")
        if not os.path.isfile(config_path):
            message = f"model config not found at {config_path!r}, url {url!r} specified an invalid model"
            raise RuntimeError(message)

    def _parse_json(self, output: str):
        _end = output.rfind("```")
        _start = output.find("```json")
        if _end != -1 and _start != -1:
            json_str = output[_start + len("```json") : _end].strip()
        else:
            json_str = output
        try:
            return loads(json_str)
        except Exception as e:
            logger.info(f"parse json failed {json_str}, info: {e}")
            return output

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def acall(
        self, prompt: Union[str, List[str], List[Dict], List[List[Dict]]], **kwargs
    ) -> Union[str, List[str]]:
        """
        Perform inference on the given prompt and return the result asynchronously.

        Args:
            prompt (Union[str, List[str], List[Dict], List[List[Dict]]]): Input prompt
                with raw string or OpenAI-style message format.

        Returns:
            str: Inference result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        return await asyncio.to_thread(lambda: self(prompt, **kwargs))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    def call_with_json_parse(
        self, prompt: Union[str, List[str], List[Dict], List[List[Dict]]], **kwargs
    ) -> Union[Any, List[Any]]:
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        Args:
            prompt (Union[str, List[str], List[Dict], List[List[Dict]]]): Input prompt
                with raw string or OpenAI-style message format.

        Returns:
            Any: Parsed result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """

        res = self(prompt, **kwargs)

        if isinstance(res, list):
            output = []
            for item in res:
                output.append(self._parse_json(item))
            return output
        else:
            return self._parse_json(res)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, max=60),
        reraise=True,
    )
    async def acall_with_json_parse(
        self, prompt: Union[str, List[str], List[Dict], List[List[Dict]]], **kwargs
    ) -> Union[Any, List[Any]]:
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        Args:
            prompt (Union[str, List[str], List[Dict], List[List[Dict]]]): Input prompt
                with raw string or OpenAI-style message format.

        Returns:
            Any: Parsed result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """

        res = await self.acall(prompt, **kwargs)
        if isinstance(res, list):
            output = []
            for item in res:
                output.append(self._parse_json(item))
            return output
        else:
            return self._parse_json(res)

    def invoke(
        self,
        variables: Union[Dict, List[Dict]],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
        with_except: bool = True,
        **kwargs,
    ):
        """
        Call the model and process the result.
        The default implementation is OpenAI API compatible, supporting streaming and tool calls but not batch requests.
        Args:
            variables (Union[Dict, List[Dict]]): Variables used to build the prompt.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.
            with_except (bool, optional): Whether to raise an exception if an error occurs. Defaults to False.

        Returns:
            List: Processed result list.
        """
        list_input = True
        if not isinstance(variables, list):
            list_input = False
            variables = [variables]
        tools = kwargs.get("tools", None)
        if tools:
            with_json_parse = False

        outputs = []
        for item in variables:
            prompt = prompt_op.build_prompt(item)
            if isinstance(prompt, list):
                prompt = ""
                kwargs["messages"] = prompt
            logger.debug(f"Prompt: {prompt}")
            response = ""
            try:
                response = (
                    self.call_with_json_parse(prompt=prompt, **kwargs)
                    if with_json_parse
                    else self(prompt, **kwargs)
                )
                if tools:
                    outputs.append(response)
                result = prompt_op.parse_response(
                    response, model=self.model, **variables
                )
                logger.debug(f"Result: {result}")
                outputs.append(response)
            except Exception as e:
                outputs.append(None)
                import traceback

                logger.info(
                    f"Error {e} during invocation: {traceback.format_exc()}. prompt={prompt} response={response}"
                )

                if with_except:
                    raise RuntimeError(
                        f"LLM invoke exception, info: {e}\nllm input: \n{prompt}\nllm output: \n{response}"
                    )
        if not list_input:
            return outputs[0]
        return outputs

    async def ainvoke(
        self,
        variables: Union[Dict, List[Dict]],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
        with_except: bool = True,
        **kwargs,
    ):
        """
        Call the model and process the result.
        The default implementation is OpenAI API compatible, supporting streaming and tool calls but not batch requests.
        Args:
            **kwargs:
            variables (Union[Dict, List[Dict]]): Variables used to build the prompt.
            prompt_op (PromptABC): Prompt operation object for building and parsing prompts.
            with_json_parse (bool, optional): Whether to attempt parsing the response as JSON. Defaults to True.
            with_except (bool, optional): Whether to raise an exception if an error occurs. Defaults to False.
        Returns:
            List: Processed result list.
        """
        list_input = True
        if not isinstance(variables, list):
            list_input = False
            variables = [variables]
        tools = kwargs.get("tools", None)
        if tools:
            with_json_parse = False
        outputs = []
        for item in variables:
            prompt = prompt_op.build_prompt(item)
            # logger.info(f"Prompt: {prompt}")
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
                        outputs.append(response)
                    else:
                        result = prompt_op.parse_response(
                            response, model=self.model, **variables
                        )
                        outputs.append(result)
                        logger.debug(f"Result: {result}")
                except Exception as e:
                    outputs.append(None)
                    import traceback

                    logger.info(
                        f"Error {e} during invocation: {traceback.format_exc()} prompt={prompt} response={response}"
                    )
                    if with_except:
                        raise RuntimeError(
                            f"LLM invoke exception, info: {e}\nllm input: \n{prompt}\nllm output: \n{response}"
                        )
        if not list_input:
            return outputs[0]
        return outputs

    def check(self):
        if not self.enable_check:
            return
        from kag.common.conf import KAG_PROJECT_CONF

        if (
            hasattr(KAG_PROJECT_CONF, "llm_config_check")
            and KAG_PROJECT_CONF.llm_config_check
        ):
            try:
                self.__call__("Are you OK?")
            except Exception as e:
                logger.error("LLM config check failed!")
                raise e
