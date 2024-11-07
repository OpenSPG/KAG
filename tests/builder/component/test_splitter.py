# -*- coding: utf-8 -*-

import copy
import unittest
import os
from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock

from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.splitter.outline_splitter import OutlineSplitter
from kag.builder.component.reader.docx_reader import DocxReader


from kag.interface import SplitterABC
from kag.builder.model.chunk import Chunk

llm_config = {
    "type": "maas",
    "base_url": "https://api.deepseek.com",
    "api_key": "key",
    "model": "deepseek-chat",
}


def test_length_splitter():
    splitter = SplitterABC.from_config(
        {"type": "length", "split_length": 20, "window_length": 10}
    )
    content = "The quick brown fox jumps over the lazy dog. " * 4
    sentences = splitter.split_sentence(content)
    assert len(sentences) == 4

    chunk = Chunk(id=1, name="test", content=content)
    chunks = splitter.invoke(chunk)
    assert len(chunks) > 1


def test_outline_splitter():
    splitter = SplitterABC.from_config(
        {
            "type": "outline",
            "llm": copy.deepcopy(llm_config),
        }
    )
    with open("../data/test_txt.txt", "r") as reader:
        content = reader.read()
    chunk = Chunk(id=1, name="test", content=content)

    chunks = splitter.invoke(chunk)
    assert len(chunks) > 0 and isinstance(chunks[0], Chunk)


def test_semantic_splitter():
    splitter = SplitterABC.from_config(
        {
            "type": "semantic",
            "llm": copy.deepcopy(llm_config),
        }
    )
    with open("../data/test_txt.txt", "r") as reader:
        content = reader.read()
    chunk = Chunk(id=1, name="test", content=content)

    chunks = splitter.invoke(chunk)
    assert len(chunks) > 0 and isinstance(chunks[0], Chunk)


if __name__ == "__main__":
    unittest.main()
