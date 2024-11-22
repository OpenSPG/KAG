# -*- coding: utf-8 -*-

import os

import copy
from kag.interface import RecordParserABC
from kag.builder.model.chunk import Chunk

pwd = os.path.dirname(__file__)


def test_dict_parser():
    parser = RecordParserABC.from_config(
        {
            "type": "dict",
            "id_col": "data_id",
            "name_col": "data_name",
            "content_col": "data_content",
        }
    )
    content = {
        "data_id": "111",
        "data_name": "222",
        "data_content": "hello.",
        "extra": "Nice.",
    }
    chunks = parser.invoke(copy.deepcopy(content))
    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
    chunk = chunks[0]
    assert chunk.id == content["data_id"]
    assert chunk.name == content["data_name"]
    assert chunk.content == content["data_content"]
    assert chunk.kwargs["extra"] == content["extra"]


def test_text_parser():
    parser = RecordParserABC.from_config({"type": "txt"})
    text = "您好！"
    chunks = parser.invoke(text)
    assert len(chunks) == 1 and chunks[0].content == text

    file_path = os.path.join(pwd, "../data/test_txt.txt")
    chunks = parser.invoke(file_path)
    with open(file_path) as f:
        content = f.read()
    chunks = parser.invoke(file_path)
    assert len(chunks) == 1
    assert chunks[0].content == content
    assert chunks[0].id == Chunk.generate_hash_id(file_path)


def test_docx_parser():
    parser = RecordParserABC.from_config({"type": "docx"})

    file_path = os.path.join(pwd, "../data/test_docx.docx")
    chunks = parser.invoke(file_path)
    # Assert the expected result
    assert len(chunks) == 30
    assert len(chunks[0].content) > 0


def test_md_parser():
    parser = RecordParserABC.from_config({"type": "md", "cut_depth": 1})
    file_path = os.path.join(pwd, "../data/test_markdown.md")
    chunks = parser.invoke(file_path)
    assert len(chunks) > 0
    assert chunks[0].name == "test_markdown#0"


def test_pdf_parser():
    parser = RecordParserABC.from_config({"type": "pdf"})

    page = "Header\nContent 1\nContent 2\nFooter"
    watermark = "Header"
    expected = ["Content 1", "Content 2"]
    result = parser._process_single_page(
        page, watermark, remove_header=True, remove_footnote=True
    )
    assert result == expected
    file_path = os.path.join(pwd, "../data/test_pdf.pdf")
    chunks = parser.invoke(file_path)
    assert chunks[0].name == "test_pdf#0"


def test_yuque_parser():
    parser = RecordParserABC.from_config({"type": "yuque", "cut_depth": 1})
    chunks = parser.invoke(
        "f6QiFu1gIDEGJIsI6jziOWbE7E9MsFkipeV69NHq@https://yuque-api.antfin-inc.com/api/v2/repos/un8gkl/kg7h1z/docs/odtmme"
    )
    assert chunks[0].name == "项目立项#0"
