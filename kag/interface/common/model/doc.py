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

from typing import Dict, Any


class Doc:
    def __init__(
        self,
        id: str,
        name: str,
        content: str,
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.content = content
        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def hash_key(self):
        from kag.common.utils import generate_hash_id

        return generate_hash_id(f"{self.id}{self.name}{self.content}")

    def __str__(self):
        tmp = {
            "id": self.id,
            "name": self.name,
            "content": (
                self.content if len(self.content) <= 64 else self.content[:64] + " ..."
            ),
        }
        return f"<Chunk>: {tmp}"

    __repr__ = __str__

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "properties": self.kwargs,
        }

    @classmethod
    def from_dict(cls, input_: Dict[str, Any]):
        return cls(
            id=input_.get("id"),
            name=input_.get("name"),
            content=input_.get("content"),
            **input_.get("properties", {}),
        )
