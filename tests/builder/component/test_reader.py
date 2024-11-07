# -*- coding: utf-8 -*-

import json
import pandas as pd
import os


from kag.interface import SourceReaderABC
from unittest.mock import patch, mock_open, MagicMock
from kag.builder.model.chunk import Chunk, ChunkTypeEnum

dir_path = os.path.dirname(__file__)


def test_text_reader():
    reader = SourceReaderABC.from_config({"type": "txt"})
    text = "您好！"
    chunks = reader.invoke(text)
    assert len(chunks) == 1 and chunks[0].content == text

    file_path = "../data/test_txt.txt"
    chunks = reader.invoke(file_path)
    with open(file_path) as f:
        content = f.read()
    chunks = reader.invoke(file_path)
    assert len(chunks) == 1
    assert chunks[0].content == content
    assert chunks[0].id == Chunk.generate_hash_id(file_path)


def test_docx_reader():
    reader = SourceReaderABC.from_config({"type": "docx"})

    chunks = reader.invoke("../data/test_docx.docx")
    # Assert the expected result
    assert len(chunks) == 30
    assert len(chunks[0].content) > 0


def test_json_reader():
    reader = SourceReaderABC.from_config(
        {"type": "json", "name_col": "title", "content_col": "text"}
    )
    json_file_path = os.path.join(dir_path, "../data/test_json.json")

    with open(json_file_path, "r") as r:
        json_string = r.read()
    json_content = json.loads(json_string)
    # read from json file
    chunks = reader.invoke(json_file_path)
    assert len(chunks) == len(json_content)
    for chunk, json_item in zip(chunks, json_content):
        assert chunk.content == json_item["text"]
        assert chunk.name == json_item["title"]

    # read from json string directly
    chunks = reader.invoke(json_string)
    assert len(chunks) == len(json_content)
    for chunk, json_item in zip(chunks, json_content):
        assert chunk.content == json_item["text"]
        assert chunk.name == json_item["title"]


def test_csv_reader():
    reader = SourceReaderABC.from_config(
        {"type": "csv", "id_col": "idx", "name_col": "title", "content_col": "text"}
    )
    file_path = os.path.join(dir_path, "../data/test_csv.csv")
    chunks = reader.invoke(file_path)

    data = pd.read_csv(file_path)
    assert len(chunks) == len(data)
    for idx in range(len(chunks)):
        chunk = chunks[idx]
        row = data.iloc[idx]
        assert str(chunk.id) == str(row.idx)
        assert chunk.name == row.title
        assert chunk.content == row.text


def test_md_reader():
    reader = SourceReaderABC.from_config({"type": "md", "cut_depth": 1})
    file_path = os.path.join(dir_path, "../data/test_markdown.md")
    chunks = reader.invoke(file_path)
    assert len(chunks) > 0
    assert chunks[0].name == "test_markdown#0"


def test_pdf_reader():
    reader = SourceReaderABC.from_config({"type": "pdf"})

    page = "Header\nContent 1\nContent 2\nFooter"
    watermark = "Header"
    expected = ["Content 1", "Content 2"]
    result = reader._process_single_page(
        page, watermark, remove_header=True, remove_footnote=True
    )
    assert result == expected
    file_path = os.path.join(dir_path, "../data/test_pdf.pdf")
    chunks = reader.invoke(file_path)
    assert chunks[0].name == "test_pdf#0"


def test_yuque_reader():
    reader = SourceReaderABC.from_config(
        {
            "type": "yuque",
            "token": "1yPz1LbE20FmXvemCDVwjlSHpAp18qtEu7wcjCfv",
            "cut_depth": 1,
        }
    )
    from kag.builder.component import MarkDownReader

    assert isinstance(reader.markdown_reader, MarkDownReader)

    chunks = reader.invoke(
        "https://yuque-api.antfin-inc.com/api/v2/repos/ob46m2/it70c2/docs/bnp80qitsy5vqoa5"
    )
    assert chunks[0].content[:6] == "1、建设目标"
