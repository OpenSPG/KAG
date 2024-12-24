# -*- coding: utf-8 -*-

import json
import pandas as pd
import os


from kag.interface import ScannerABC
from kag.builder.model.chunk import Chunk, ChunkTypeEnum

pwd = os.path.dirname(__file__)


def test_json_scanner():
    scanner = ScannerABC.from_config({"type": "json", "rank": 0, "world_size": 1})
    file_path = os.path.join(pwd, "../data/test_json.json")

    with open(file_path, "r") as r:
        json_string = r.read()
    json_content = json.loads(json_string)

    data = scanner.invoke(file_path)
    assert len(data) == len(json_content)
    for l, r in zip(data, json_content):
        assert l == r

    scanner_1 = ScannerABC.from_config({"type": "json", "rank": 0, "world_size": 2})
    scanner_2 = ScannerABC.from_config({"type": "json", "rank": 1, "world_size": 2})

    data_1 = scanner_1.invoke(file_path)
    data_2 = scanner_2.invoke(file_path)
    data = data_1 + data_2
    assert len(data) == len(json_content)
    for l, r in zip(data, json_content):
        assert l == r


def test_csv_scanner():
    file_path = os.path.join(pwd, "../data/test_csv.csv")
    scanner = ScannerABC.from_config({"type": "csv", "rank": 0, "world_size": 1})
    csv_content = []
    for _, item in pd.read_csv(file_path, dtype=str).iterrows():
        csv_content.append(item.to_dict())
    data = scanner.invoke(file_path)

    assert len(data) == len(csv_content)
    for l, r in zip(data, csv_content):
        assert l == r

    scanner_1 = ScannerABC.from_config({"type": "csv", "rank": 0, "world_size": 2})
    scanner_2 = ScannerABC.from_config({"type": "csv", "rank": 1, "world_size": 2})

    data_1 = scanner_1.invoke(file_path)
    data_2 = scanner_2.invoke(file_path)
    data = data_1 + data_2
    assert len(data) == len(csv_content)
    for l, r in zip(data, csv_content):
        assert l == r


def test_csv_scanner_with_cols():
    file_path = os.path.join(pwd, "../data/test_csv.csv")
    scanner = ScannerABC.from_config(
        {"type": "csv", "rank": 0, "world_size": 1, "col_names": ["title", "text"]}
    )
    csv_content = []
    for _, item in pd.read_csv(file_path, dtype=str).iterrows():
        csv_content.append(item.to_dict())
    data = scanner.invoke(file_path)

    assert len(data) == len(csv_content) * 2

    scanner_1 = ScannerABC.from_config(
        {"type": "csv", "rank": 0, "world_size": 2, "col_names": ["title", "text"]}
    )
    scanner_2 = ScannerABC.from_config(
        {"type": "csv", "rank": 1, "world_size": 2, "col_names": ["title", "text"]}
    )

    data_1 = scanner_1.invoke(file_path)
    data_2 = scanner_2.invoke(file_path)
    data = data_1 + data_2
    assert len(data) == len(csv_content) * 2

    file_path = os.path.join(pwd, "../data/test_csv_headerless.csv")
    scanner = ScannerABC.from_config(
        {"type": "csv", "rank": 0, "world_size": 1, "col_ids": [0, 1], "header": False}
    )
    csv_content = []
    for _, item in pd.read_csv(file_path, dtype=str, header=None).iterrows():
        csv_content.append(item.to_dict())
    data = scanner.invoke(file_path)

    assert len(data) == len(csv_content) * 2


def test_file_scanner():
    scanner = ScannerABC.from_config({"type": "file"})
    file_name = "test.txt"
    out = scanner.invoke(file_name)
    assert out == [file_name]

    file_name2 = (
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    )
    out = scanner.invoke(file_name2)
    assert (
        isinstance(out, list)
        and len(out) == 1
        and os.path.basename(out[0]) == "dummy.pdf"
    )


def test_directory_scanner():
    scanner = ScannerABC.from_config({"type": "dir", "file_suffix": "json"})
    dir_path = os.path.join(pwd, "../data/")
    all_data = scanner.invoke(dir_path)
    for item in all_data:
        assert os.path.exists(item)
        assert item.endswith("json")

    scanner_1 = ScannerABC.from_config(
        {"type": "dir", "file_suffix": "json", "rank": 0, "world_size": 2}
    )
    scanner_2 = ScannerABC.from_config(
        {"type": "dir", "file_suffix": "json", "rank": 1, "world_size": 2}
    )
    data_1 = scanner_1.invoke(dir_path)
    data_2 = scanner_2.invoke(dir_path)
    assert len(all_data) == len(data_1) + len(data_2)

    scanner = ScannerABC.from_config({"type": "dir", "file_pattern": ".*txt$"})
    all_data = scanner.invoke(dir_path)

    for item in all_data:
        assert os.path.exists(item)
        assert item.endswith("txt")


def test_yuque_scanner():
    token = "pKjtrFOr7w4QUzBTEjXdpV33QzVEHR49kvkZmGFV"
    scanner = ScannerABC.from_config({"type": "yuque", "token": token})
    urls = scanner.invoke(
        "https://yuque-api.antfin-inc.com/api/v2/repos/un8gkl/kg7h1z/docs/"
    )
    for url in urls:
        token, rea_url = url.split("@", 1)
        assert token == scanner.token

    urls = scanner.invoke(
        ["https://yuque-api.antfin-inc.com/api/v2/repos/un8gkl/kg7h1z/docs/"]
    )
    assert (
        len(urls) == 1
        and urls[0]
        == f"{token}@https://yuque-api.antfin-inc.com/api/v2/repos/un8gkl/kg7h1z/docs/"
    )
