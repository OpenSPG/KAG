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

import logging
import os
import json
import hashlib
import shutil
import random

import chromadb
from kag.interface import PromptABC

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


def split_to_list(txt_list, limit_len) -> list:
    rst = []
    tmp = ""
    for l in txt_list:
        if len(tmp) < limit_len:
            tmp += f"\n{l}"
            continue
        rst.append(tmp.strip())
        tmp = l
    if len(tmp) > 0:
        rst.append(tmp.strip())
    return rst


@PromptABC.register("default_table_context")
class TableContextPrompt(PromptABC):
    template_zh = """
# 你的任务
仔细阅读表格及其上下文信息，给表格总结一个整体摘要信息，然后输出表格每一行数据的摘要信息。

# 操作指南
1. 对表格的每一行，标有row_index_<number>，先判断该行数据属于表头还是数据行，然后总结这一行数据的摘要。
2. 摘要不允许重复行中的内容和数据。
3. 确保读者通过摘要，可以完全理解该行数据的信息。

# 输出格式
json格式，例子:
```json
{
  "table_summary": "Table Summary",
  "rows": [
    {"index": 0, "type": "header", "summary": "表头摘要"},
    {"index": 1, "type": "header", "summary": "多层表头，第二行表头摘要"},
    {"index": 2, "type": "data"  , "summary": "第一行数据摘要"}
  ]
}
```
# 输入表格及其上下文信息
$input

# 你的json输出
""".strip()

    template_en = """
# Your Task
Carefully read the table and its contextual information, then summarize the overall content of the table as a whole. After that, provide a summary for each row of the table.

# Instructions
1. For each row in the table, marked as row_index_<number>, first determine whether the row is a header or a data row, then summarize the information in that row.
2. The summary should not repeat the contents or data from the row itself.
3. Ensure readers can fully understand the information of that row through the summary.

# Output Format
JSON format, example:
```json
{
  "table_summary": "Table Summary",
  "rows": [
    {"index": 0, "type": "header", "summary": "Header row summary"},
    {"index": 1, "type": "header", "summary": "Second row of header with its summary"},
    {"index": 2, "type": "data"  , "summary": "First row of data summary"}
  ]
}
```
# Input Table and Contextual Information
$input

# Your JSON Output
""".strip()

    @property
    def template_variables(self) -> list[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            try:
                rsp = json.loads(rsp)
            except json.decoder.JSONDecodeError as e:
                logging.exception("json_str=%s", rsp)
                raise e
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        summary = rsp["table_summary"]
        rows = rsp["rows"]
        return summary, rows


from kag.solver.utils import init_prompt_with_fallback

table_context_prompt = init_prompt_with_fallback("table_context", "default")

from kag.interface import LLMClient

llm: LLMClient = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])


def _table_to_row_col_index_df(df, update_column=False):
    new_df = df.copy()
    new_df.insert(0, "row_index_0", [f"row_index_{i+1}" for i in range(len(new_df))])
    new_columns = []
    for i, c in enumerate(new_df.columns):
        if 0 == i:
            new_columns.append(c)
            continue
        new_columns.append(f"{c}[column_index_{i-1}]")
    if update_column:
        new_df.columns = new_columns
    return new_df


def get_table_data(file_name, prev, post, table_df: pd.DataFrame, use_raw_table_df=False):
    if use_raw_table_df:
        return [f"{table_df.to_markdown(index=False)}"]
    tmp_df = _table_to_row_col_index_df(df=table_df)
    table_index_md = tmp_df.to_markdown(index=False)
    input_str = f"{prev}\n\n{table_index_md}\n\n{post}"
    table_summary, row_summary_list = llm.invoke(
        variables={"input": input_str},
        prompt_op=table_context_prompt,
        with_json_parse=True,
        with_except=True,
        with_cache=True,
    )
    try:
        header_idx_list = []
        for row_summary in row_summary_list:
            if row_summary["type"] != "header":
                continue
            row_index = row_summary["index"]
            header_idx_list.append(row_index)
        header_idx_list = sorted(header_idx_list)
        is_consecutive_from_zero = sorted(set(header_idx_list)) == list(range(len(set(header_idx_list))))
        if not is_consecutive_from_zero:
            raise RuntimeWarning("分离的header表")

        header_list = None
        for row_summary in row_summary_list:
            if row_summary["type"] != "header":
                continue
            row_index = row_summary["index"]
            new_header_list = None
            if 0 == row_index:
                new_header_list = table_df.columns
            else:
                new_header_list = table_df.iloc[row_index - 1].tolist()
            if header_list is None:
                header_list = new_header_list
            else:
                header_list = zip(header_list, new_header_list)

        if header_list is not None:
            header_list = list(header_list)
        rst_row_summary_list = []
        for row_summary in row_summary_list:
            if row_summary["type"] != "data":
                continue
            row_index = row_summary["index"]
            if 0 == row_index:
                data = table_df.columns
            else:
                data = table_df.iloc[row_index - 1].tolist()
            if header_list is not None:
                df = pd.DataFrame([data], columns=header_list)
            else:
                df = pd.DataFrame([data])
            content = df.to_markdown(index=False)
            rst_row_summary_list.append(
                f"{table_summary}\n{row_summary['summary']}\n{content}"
            )
    except:
        logging.exception("convert table error, file_name=%s", file_name)
        return [f"{table_summary}\n{table_df.to_markdown(index=False)}"]
    return rst_row_summary_list


def convert_data(item, limitlen) -> list:
    prev_text_list = item["pre_text"]
    prev_text_list = [s for s in prev_text_list if s != "."]

    post_text_list = item["post_text"]
    post_text_list = [s for s in post_text_list if s != "."]

    table_row_list = item["table"]
    columns = table_row_list[0]
    data = table_row_list[1:]
    table_df = pd.DataFrame(data=data, columns=columns)

    prev_chunk_list = split_to_list(prev_text_list, limitlen)
    post_chunk_list = split_to_list(post_text_list, limitlen)
    return (
        prev_chunk_list
        + get_table_data(
            item["filename"],
            prev_chunk_list[-1] if len(prev_chunk_list) > 0 else "",
            post_chunk_list[0] if len(post_chunk_list) > 0 else "",
            table_df=table_df,
            use_raw_table_df=True,
        )
        + post_chunk_list
    )


def save_data(item, collection):
    file_name = item["filename"]
    print(file_name)
    chunk_len = 500
    documents = convert_data(item, chunk_len)
    documents = [f"{i:02d}. {d}" for i, d in enumerate(documents)]
    metadatas = [{"file_name": f"{file_name}_{chunk_len}"} for doc in documents]
    ids = [f"{file_name}_{chunk_len}_{i}" for i, _ in enumerate(documents)]

    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chromadb_path = os.path.join(current_dir, "chunk_chromadb_raw_table")
    os.makedirs(chromadb_path, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=chromadb_path)
    collection = chroma_client.create_collection(name="chunk", get_or_create=True)

    id_set = None
    _finqa_file_to_qa_map = load_finqa_data()
    print(f"all_data={len(_finqa_file_to_qa_map)}")
    idx = 0
    for file_name, _item_list in _finqa_file_to_qa_map.items():
        idx += 1
        print(f"now_idx={idx}")
        if id_set is not None and file_name not in id_set:
            continue
        try:
            save_data(_item_list[0], collection)
        except:
            print(f"error file name: {file_name}")
