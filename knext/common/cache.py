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

from cachetools import TTLCache


class LinkCache:
    def __init__(self, maxsize: int = 500, ttl: int = 60):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    @property
    def cache(self):
        return self._cache

    def put(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache.get(key)


class SchemaCache:
    def __init__(self, maxsize: int = 10, ttl: int = 300):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    @property
    def cache(self):
        return self._cache

    def put(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache.get(key)
