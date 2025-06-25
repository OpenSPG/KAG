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

import os
import json
import hashlib
import shutil
import random

import pandas as pd
from neo4j import GraphDatabase

from kag.builder.runner import BuilderChainRunner
from kag.common.conf import KAG_CONFIG


def load_finqa_data() -> map:
    """
    load data
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "data", "test.json")
    with open(file_name, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print("finqa data list len " + str(len(data_list)))
    for _idx, data in enumerate(data_list):
        data["index"] = _idx

    file_to_qa_map = {}
    for data in data_list:
        finqa_filename = data["filename"]
        if finqa_filename not in file_to_qa_map:
            file_to_qa_map[finqa_filename] = []
        file_to_qa_map[finqa_filename].append(data)
    return file_to_qa_map


def convert_finqa_to_md_file(item: dict) -> str:
    """
    convert finqa data to md file
    """
    _file_name: str = item["filename"]
    _file_name = _file_name.replace("/", "_")
    prev_text_list = item["pre_text"]
    prev_text_list = [s for s in prev_text_list if s != "."]
    prev_text = "\n".join(prev_text_list)
    post_text_list = item["post_text"]
    post_text_list = [s for s in post_text_list if s != "."]
    post_text = "\n".join(post_text_list)
    table_row_list = item["table"]
    columns = table_row_list[0]
    data = table_row_list[1:]
    table_df = pd.DataFrame(data=data, columns=columns)
    table_md_str = table_df.to_markdown(index=False)
    md_file_tmp = f"/tmp/tableeval/{_file_name}.md"
    if os.path.exists(md_file_tmp):
        os.remove(md_file_tmp)
    os.makedirs(os.path.dirname(md_file_tmp), exist_ok=True)
    with open(md_file_tmp, "w", encoding="utf-8") as f:
        f.write(
            f"# {_file_name}\n\n"
            + prev_text
            + "\n\n"
            + table_md_str
            + "\n\n"
            + post_text
        )
    return md_file_tmp


def build_finqa_graph(item):
    """
    build graph
    """
    clear_neo4j_data("finqa")
    current_working_directory = os.getcwd()
    ckpt_path = os.path.join(current_working_directory, "ckpt")
    if os.path.exists(ckpt_path):
        shutil.rmtree(ckpt_path)
    _file_name = convert_finqa_to_md_file(item)
    build_md_file(_file_name)


def build_md_file(md_file: str):
    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["finqa_builder_pipeline"]
    )
    runner.invoke(md_file)


def clear_neo4j_data(db_name):
    """
    清空neo4j数据
    """

    # 定义数据库连接信息
    uri = "neo4j://localhost:7687"
    username = "neo4j"
    password = "neo4j@openspg"
    # 创建数据库驱动
    driver = GraphDatabase.driver(uri, auth=(username, password))

    def delete_all_nodes_and_relationships(tx):
        # 删除所有节点
        tx.run("MATCH (n) DETACH DELETE n")

    with driver.session(database=db_name) as session:
        session.execute_write(delete_all_nodes_and_relationships)


from kag.examples.finqa.builder.table_and_text_extractor import TableAndTextExtractor
from kag.examples.finqa.builder.length_splitter import LineLengthSplitter
from kag.examples.finqa.builder.prompt.table_context import TableContextPrompt
from kag.examples.finqa.builder.prompt.table_row_col_summary import (
    TableRowColSummaryPrompt,
)

if __name__ == "__main__":
    _finqa_file_to_qa_map = load_finqa_data()
    for file_name, _item_list in _finqa_file_to_qa_map.items():
        for _item in _item_list:
            build_finqa_graph(_item)
            break
