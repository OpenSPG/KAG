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

import io
import os
import threading
import tarfile
import requests
from typing import Any, Union, Iterable, Dict
from kag.common.vectorizer.vectorizer import Vectorizer


EmbeddingVector = Iterable[float]

LOCAL_MODEL_MAP = {}
