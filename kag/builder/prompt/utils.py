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
import logging
from kag.interface import PromptABC

logger = logging.getLogger(__name__)


def init_prompt_with_fallback(prompt_name, biz_scene):
    try:
        return PromptABC.from_config({"type": f"{biz_scene}_{prompt_name}"})
    except Exception as e:
        logger.debug(
            f"fail to initialize prompts with biz scene {biz_scene}, fallback to default biz scene, info: {e}"
        )

        return PromptABC.from_config({"type": f"default_{prompt_name}"})
