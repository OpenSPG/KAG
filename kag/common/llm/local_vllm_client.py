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
import threading
import logging
import copy
from typing import Dict, List, Union
from kag.interface import LLMClient, PromptABC

logger = logging.getLogger()
LOCAL_MODEL_MAP = {}


@LLMClient.register("local_vllm_client")
@LLMClient.register("local_vllm")
class LocalVLLMClient(LLMClient):
    _LOCK = threading.Lock()
    """ VLLM based client, supporting batch requests but no streaming or tool calls."""

    def __init__(
        self,
        path: str,
        url: str = None,
        max_rate: float = 1000,
        time_period: float = 1,
        is_vgpu: bool = True,
        llm_init_params: Dict = None,
        sampling_params: Dict = None,
        **kwargs,
    ):
        """
        Initializes the MockLLMClient instance.
        """
        name = kwargs.pop("name", None)
        if not name:
            name = "local_vllm"

        super().__init__(name, max_rate, time_period)

        if llm_init_params is None:
            self.llm_init_params = {
                "dtype": "float16",
                "max_model_len": 20000,
                "disable_custom_all_reduce": True,
            }

        else:
            self.llm_init_params = dict(llm_init_params)

        self.is_vgpu = is_vgpu

        if self.is_vgpu:
            max_num_batched_tokens = self.llm_init_params["max_model_len"]
            self.llm_init_params.update({"enforce_eager": False})
            self.llm_init_params.update(
                {"max_num_batched_tokens": max_num_batched_tokens}
            )
        else:
            self.llm_init_params.update({"gpu_memory_utilization": 0.9})
            self.llm_init_params.update({"swap_space": 4})
            self.llm_init_params.update({"enable_prefix_caching": False})
            self.llm_init_params.update({"enforce_eager": False})

        from vllm import SamplingParams

        if sampling_params is None:
            self.sampling_params = SamplingParams()
        else:
            self.sampling_params = SamplingParams(**sampling_params)

        self.model_path = os.path.expanduser(path)
        self.url = url
        config_path = os.path.join(self.model_path, "config.json")
        if not os.path.isfile(config_path):
            if self.url is None:
                message = f"model not found at {path!r}, nor model url specified"
                raise RuntimeError(message)
            logger.info("Model file not found in path, start downloading...")
            self._download_model(self.model_path, self.url)

        with LocalVLLMClient._LOCK:
            if self.model_path in LOCAL_MODEL_MAP:
                logger.info("Found existing model, reuse.")
                model, tokenizer = LOCAL_MODEL_MAP[self.model_path]
            else:
                model, tokenizer = self._load_model(self.model_path)
                LOCAL_MODEL_MAP[self.model_path] = (model, tokenizer)
            self.model = model
            self.tokenizer = tokenizer

    def _load_model(self, model_path: str):
        from vllm import LLM
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        llm_init_params = copy.deepcopy(self.llm_init_params)
        llm_init_params["model"] = model_path

        self.llm = LLM(**llm_init_params)

    def __call__(
        self, prompt: Union[str, List[str], List[Dict], List[List[Dict]]], **kwargs
    ) -> Union[str, List[str]]:
        if isinstance(prompt, str):
            prompt = [prompt]
        if isinstance(prompt[0], str):
            # use generate for string format
            func = self.model.generate
        else:
            # use chat for OpenAI-style message format
            func = self.model.chat

        # vllm.LLM.generate/chat will always return list responses
        results = func(prompt, self.sampling_params, **kwargs)

        output = [x.outputs[0].text for x in results]
        if len(output) == 1:
            return output[0]
        return output

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

        prompts = [prompt_op.build_prompt(x) for x in variables]

        try:
            responses = (
                self.call_with_json_parse(prompts, **kwargs)
                if with_json_parse
                else self(prompts, **kwargs)
            )
            results = [
                prompt_op.parse_response(x, model=self.model, **variables)
                for x in responses
            ]
            logger.debug(f"Results: {results}")
            if not list_input:
                return results[0]
            return results
        except Exception as e:
            import traceback

            logger.info(
                f"Error {e} during invocation: {traceback.format_exc()}. prompt={prompts} response={responses}"
            )
            if with_except:
                raise RuntimeError(
                    f"LLM invoke exception, info: {e}\nllm input: \n{prompts}\nllm output: \n{responses}"
                )

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

        prompts = [prompt_op.build_prompt(x) for x in variables]

        async with self.limiter:
            try:
                responses = await (
                    self.acall_with_json_parse(prompts, **kwargs)
                    if with_json_parse
                    else self.acall(prompts, **kwargs)
                )
                results = [
                    prompt_op.parse_response(x, model=self.model, **variables)
                    for x in responses
                ]
                logger.debug(f"Results: {results}")
                if not list_input:
                    return results[0]
                return results

            except Exception as e:
                import traceback

                logger.info(
                    f"Error {e} during invocation: {traceback.format_exc()} prompt={prompts} response={responses}"
                )
                if with_except:
                    raise RuntimeError(
                        f"LLM invoke exception, info: {e}\nllm input: \n{prompts}\nllm output: \n{responses}"
                    )
