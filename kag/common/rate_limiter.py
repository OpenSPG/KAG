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
import threading
import time
from collections import deque


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


class SyncRateLimiter:
    def __init__(self, max_rate: int, time_period: float = 1.0):
        """
        Initialize the rate limiter.

        :param max_rate: The maximum number of requests allowed within the time window.
        :param time_period: The length of the time window in seconds.
        """
        self.max_rate = max_rate
        self.time_period = time_period
        self.lock = threading.Lock()
        self.call_timestamps = deque()

    def acquire(self):
        """
        Acquire a permit to proceed. If the rate limit is exceeded, block and wait until a permit becomes available.
        """
        with self.lock:
            now = time.time()
            # Remove records outside the current time window
            while (
                self.call_timestamps
                and now - self.call_timestamps[0] >= self.time_period
            ):
                self.call_timestamps.popleft()

            if len(self.call_timestamps) >= self.max_rate:
                # Wait until the earliest request exits the window
                sleep_time = self.call_timestamps[0] + self.time_period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()  # Update current time after waiting
                    # Clean up expired requests again
                    while (
                        self.call_timestamps
                        and now - self.call_timestamps[0] >= self.time_period
                    ):
                        self.call_timestamps.popleft()

            # Append the timestamp of the current request
            self.call_timestamps.append(now)


class SyncRateLimiterManager:
    def __init__(self):
        self.limiter_map = {}
        self.lock = threading.Lock()

    def get_rate_limiter(
        self, name: str, max_rate: int = 1000, time_period: float = 1.0
    ):
        """
        Get or create a SyncRateLimiter instance by name in a thread-safe manner.

        :param name: Unique identifier for the rate limiter.
        :param max_rate: Maximum number of requests allowed within the time window.
        :param time_period: Length of the time window in seconds.
        :return: A thread-safe SyncRateLimiter instance.
        """
        with self.lock:
            if name not in self.limiter_map:
                self.limiter_map[name] = SyncRateLimiter(max_rate, time_period)
        return self.limiter_map[name]


SYNC_RATE_LIMITER_MANAGER = SyncRateLimiterManager()
