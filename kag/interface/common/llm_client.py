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
from typing import Union, Dict, List, Any
import logging
import traceback
from tenacity import retry, stop_after_attempt
from kag.interface import PromptABC
from kag.common.registry import Registrable


logger = logging.getLogger(__name__)


class LLMClient(Registrable):
    """
    A class that provides methods for performing inference using large language model.

    This class includes methods to call the model with a prompt, parse the response, and handle batch processing of prompts.
    """

    @retry(stop=stop_after_attempt(3))
    def __call__(self, prompt: Union[str, dict, list]) -> str:
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

    @retry(stop=stop_after_attempt(3))
    def call_with_json_parse(self, prompt: Union[str, dict, list]):
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        Args:
            prompt (Union[str, dict, list]): Input prompt for inference.

        Returns:
            Any: Parsed result.

        Raises:
            NotImplementedError: If the subclass has not implemented this method.
        """
        res = self(prompt)
        _end = res.rfind("```")
        _start = res.find("```json")
        if _end != -1 and _start != -1:
            json_str = res[_start + len("```json") : _end].strip()
        else:
            json_str = res
        try:
            json_result = loads(json_str)
        except:
            return res
        return json_result

    def invoke(
        self,
        variables: Dict[str, Any],
        prompt_op: PromptABC,
        with_json_parse: bool = True,
        with_except: bool = True,
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
        logger.debug(f"Prompt: {prompt}")
        if not prompt:
            return result
        response = ""
        try:
            response = (
                self.call_with_json_parse(prompt=prompt)
                if with_json_parse
                else self(prompt)
            )
            logger.debug(f"Response: {response}")
            result = prompt_op.parse_response(response, model=self.model, **variables)
            logger.debug(f"Result: {result}")
        except Exception as e:
            import traceback

            logger.info(f"Error {e} during invocation: {traceback.format_exc()}")
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
                logger.error(f"Error processing prompt {idx}: {e}")
                logger.debug(traceback.format_exc())
                continue
        return results

    def check(self):
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
