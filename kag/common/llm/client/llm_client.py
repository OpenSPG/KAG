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
from pathlib import Path
from typing import Union, Dict, List, Any
import logging
import traceback
import yaml

from kag.common.base.prompt_op import PromptOp
from kag.common.llm.config import *


logger = logging.getLogger(__name__)


class LLMClient:
    # Define the model type
    model: str

    config_cls_map = {
        "maas": OpenAIConfig,
        "vllm": VLLMConfig,
        "ollama": OllamaConfig,
    }

    def __init__(self, **kwargs):
        self.model = kwargs.get("model", None)
    
    @classmethod
    def get_config_cls(self,config:dict):
        client_type = config.get("client_type", None)
        return LLMClient.config_cls_map.get(client_type, None)
        
    @classmethod
    def get_llm_cls(self,config: LLMConfig):
        from kag.common.llm.client import VLLMClient,OpenAIClient,OllamaClient
        return {
            VLLMConfig: VLLMClient,
            OpenAIConfig: OpenAIClient,
            OllamaConfig: OllamaClient,
        }[config.__class__]

    @classmethod
    def from_config(cls, config: Union[str, dict]):
        """
        Initialize an LLMClient instance from a configuration file or dictionary.

        :param config: Path to a configuration file or a configuration dictionary
        :return: Initialized LLMClient instance
        :raises FileNotFoundError: If the configuration file is not found
        :raises ValueError: If the model type is unsupported
        """
        if isinstance(config, str):
            config_path = Path(config)
            if config_path.is_file():
                try:
                    with open(config_path, "r") as f:
                        nn_config = yaml.safe_load(f)
                except:
                    logger.error(f"Failed to parse config file")
                    raise
            else:
                logger.error(f"Config file not found: {config}")
                raise FileNotFoundError(f"Config file not found: {config}")
        else:
            # If config is already a dictionary, use it directly
            nn_config = config
        
        config_cls = LLMClient.get_config_cls(nn_config)
        if config_cls is None:
            logger.error(f"Unsupported model type: {nn_config.get('client_type', None)}")
            raise ValueError(f"Unsupported model type")
        llm_config = config_cls(**nn_config)
        llm_cls = LLMClient.get_llm_cls(llm_config)
        return llm_cls(llm_config)
        
            
    def __call__(self, prompt: Union[str, dict, list]) -> str:
        """
        Perform inference on the given prompt and return the result.

        :param prompt: Input prompt for inference
        :return: Inference result
        :raises NotImplementedError: If the subclass has not implemented this method
        """
        raise NotImplementedError

    def call_with_json_parse(self, prompt: Union[str, dict, list]):
        """
        Perform inference on the given prompt and attempt to parse the result as JSON.

        :param prompt: Input prompt for inference
        :return: Parsed result
        :raises NotImplementedError: If the subclass has not implemented this method
        """
        res = self(prompt)
        _end = res.rfind("```")
        _start = res.find("```json")
        if _end != -1 and _start != -1:
            json_str = res[_start + len("```json"): _end].strip()
        else:
            json_str = res
        try:
            json_result = json.loads(json_str)
        except:
            return res
        return json_result

    def invoke(self, variables: Dict[str, Any], prompt_op: PromptOp, with_json_parse: bool = True,
               with_except: bool = False):
        """
        Call the model and process the result.

        :param variables: Variables used to build the prompt
        :param prompt_op: Prompt operation object for building and parsing prompts
        :param with_json_parse: Whether to attempt parsing the response as JSON
        :param with_except: Whether to raise exception
        :return: Processed result list
        """
        result = []
        prompt = prompt_op.build_prompt(variables)
        logger.debug(f"Prompt: {prompt}")
        if not prompt:
            return result
        response = ""
        try:
            response = self.call_with_json_parse(prompt=prompt) if with_json_parse else self(prompt)
            logger.debug(f"Response: {response}")
            result = prompt_op.parse_response(response, model=self.model, **variables)
            logger.debug(f"Result: {result}")
        except Exception as e:
            import traceback
            logger.debug(f"Error {e} during invocation: {traceback.format_exc()}")
            if with_except:
                raise RuntimeError(f"call llm exception! llm output = {response} , llm input={prompt}, err={e}")
        return result

    def batch(self, variables: Dict[str, Any], prompt_op: PromptOp, with_json_parse: bool = True) -> List:
        """
        Batch process prompts.

        :param variables: Variables used to build the prompts
        :param prompt_op: Prompt operation object for building and parsing prompts
        :param with_json_parse: Whether to attempt parsing the response as JSON
        :return: List of all processed results
        """
        results = []
        prompts = prompt_op.build_prompt(variables)
        # If there is only one prompt, call the `invoke` method directly
        if isinstance(prompts, str):
            return self.invoke(variables, prompt_op, with_json_parse=with_json_parse)

        for idx, prompt in enumerate(prompts, start=0):
            logger.debug(f"Prompt_{idx}: {prompt}")
            try:
                response = self.call_with_json_parse(prompt=prompt) if with_json_parse else self(prompt)
                logger.debug(f"Response_{idx}: {response}")
                result = prompt_op.parse_response(response, idx=idx, model=self.model, **variables)
                logger.debug(f"Result_{idx}: {result}")
                results.extend(result)
            except Exception as e:
                logger.error(f"Error processing prompt {idx}: {e}")
                logger.debug(traceback.format_exc())
                continue
        return results
    