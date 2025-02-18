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

import pandas as pd

from kag.builder.runner import BuilderChainRunner
from kag.common.conf import KAG_CONFIG


def load_finqa_data() -> list:
    """
    load data
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "data", "dev.json")
    with open(file_name, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print("finqa data list len " + str(len(data_list)))
    return data_list


def convert_finqa_to_md_file(item: dict) -> str:
    """
    convert finqa data to md file
    """
    _id = item["id"]
    prev_text_list = item["pre_text"]
    prev_text = "\n".join(prev_text_list)
    post_text_list = item["post_text"]
    post_text = "\n".join(post_text_list)
    table_row_list = item["table"]
    columns = table_row_list[0]
    data = table_row_list[1:]
    table_df = pd.DataFrame(data=data, columns=columns)
    table_md_str = table_df.to_markdown(index=False)
    md5_hash = hashlib.md5()
    md5_hash.update(table_md_str.encode("utf-8"))
    hash_id = md5_hash.hexdigest()
    md_file_tmp_path = f"/tmp/tableeval/{hash_id}.md"
    if os.path.exists(md_file_tmp_path):
        os.remove(md_file_tmp_path)
    os.makedirs(os.path.dirname(md_file_tmp_path), exist_ok=True)
    with open(md_file_tmp_path, "w", encoding="utf-8") as f:
        f.write(f"# {_id}\n\n" + prev_text + "\n\n" + table_md_str + "\n\n" + post_text)
    return md_file_tmp_path


def build_finqa_graph(item):
    """
    build graph
    """
    current_working_directory = os.getcwd()
    ckpt_path = os.path.join(current_working_directory, "ckpt")
    if os.path.exists(ckpt_path):
        shutil.rmtree(ckpt_path)
    file_name = convert_finqa_to_md_file(item)
    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["finqa_builder_pipeline"]
    )
    runner.invoke(file_name)


if __name__ == "__main__":
    _data_list = load_finqa_data()
    test_i = 1
    for i, _item in enumerate(_data_list):
        if test_i is not None and i != test_i:
            continue
        _question = _item["qa"]["question"]
        _gold = _item["qa"]["answer"]
        build_finqa_graph(_item)
