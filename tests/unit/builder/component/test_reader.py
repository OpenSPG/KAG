# -*- coding: utf-8 -*-

import os

import copy
import shutil
from kag.interface import ReaderABC
from kag.builder.model.chunk import Chunk

pwd = os.path.dirname(__file__)


def test_dict_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))
    reader = ReaderABC.from_config(
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
    chunks = reader.invoke(copy.deepcopy(content))
    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
    chunk = chunks[0]
    assert chunk.id == content["data_id"]
    assert chunk.name == content["data_name"]
    assert chunk.content == content["data_content"]
    assert chunk.kwargs["extra"] == content["extra"]


def test_text_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))

    reader = ReaderABC.from_config({"type": "txt"})
    text = "您好！"
    chunks = reader.invoke(text)
    assert len(chunks) == 1 and chunks[0].content == text

    file_path = os.path.join(pwd, "../data/test_txt.txt")
    chunks = reader.invoke(file_path)
    with open(file_path) as f:
        content = f.read()
    chunks = reader.invoke(file_path)
    assert len(chunks) == 1
    assert chunks[0].content == content


def test_docx_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))

    reader = ReaderABC.from_config({"type": "docx"})

    file_path = os.path.join(pwd, "../data/test_docx.docx")
    chunks = reader.invoke(file_path)
    # Assert the expected result
    assert len(chunks) == 1
    assert len(chunks[0].content) > 0


def test_md_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))

    reader = ReaderABC.from_config({"type": "md", "cut_depth": 1})
    file_path = os.path.join(pwd, "../data/test_markdown.md")
    chunks = reader.invoke(file_path)
    assert len(chunks) > 0


def test_pdf_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))

    reader = ReaderABC.from_config({"type": "pdf"})

    page = "Header\nContent 1\nContent 2\nFooter"
    watermark = "Header"
    expected = ["Content 1", "Content 2"]
    result = reader._process_single_page(
        page, watermark, remove_header=True, remove_footnote=True
    )
    assert result == expected
    file_path = os.path.join(pwd, "../data/test_pdf.pdf")
    chunks = reader.invoke(file_path)
    assert chunks[0].name == "test_pdf#0"


def test_yuque_reader():
    if os.path.exists(os.path.join(pwd, "ckpt")):
        shutil.rmtree(os.path.join(pwd, "ckpt"))

    reader = ReaderABC.from_config({"type": "yuque", "cut_depth": 2})
    chunks = reader.invoke(
        "xxx@https://yuque-api.antfin-inc.com/api/v2/repos/un8gkl/kg7h1z/docs/odtmme"
    )
    assert len(chunks) > 0
