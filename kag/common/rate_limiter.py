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

from aiolimiter import AsyncLimiter


class RateLimiterManger:
    def __init__(self):
        self.limiter_map = {}

    def get_rate_limiter(
        self, name: str, max_rate: float = 1000, time_period: float = 1
    ):
        if name not in self.limiter_map:
            limiter = AsyncLimiter(max_rate, time_period)
            self.limiter_map[name] = limiter
        return self.limiter_map[name]


RATE_LIMITER_MANGER = RateLimiterManger()
