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
from abc import ABC, abstractmethod

from knext.common.base.chain import Chain


class BuilderChainABC(Chain, ABC):
    @abstractmethod
    def build(self, **kwargs) -> Chain:
        raise NotImplementedError(
            f"`invoke` is not currently supported for {self.__class__.__name__}."
        )

    def invoke(self, file_path, max_workers=10, **kwargs):
        chain = self.build(file_path=file_path, max_workers=max_workers, **kwargs)
        chain.invoke(input=file_path, max_workers=max_workers, **kwargs)
