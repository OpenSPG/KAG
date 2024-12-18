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

import json
import logging
import os
from typing import List


from kag.interface.builder import ExtractorABC
from kag.common.base.prompt_op import PromptOp
from kag.builder.model.chunk import Chunk
from knext.common.base.runnable import Input, Output

import os
import logging
import json
import pandas as pd
from io import StringIO

from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.component.splitter.base_table_splitter import BaseTableSplitter
from kag.builder.component.extractor.kag_extractor import KAGExtractor
from knext.common.base.runnable import Input, Output


from typing import List

import logging
import os
from typing import List


from kag.interface.builder import ExtractorABC
from kag.builder.model.sub_graph import SubGraph, Node, Edge

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class TableExtractor(ExtractorABC, BaseTableSplitter):
    """
    table extractor
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = self._init_llm()
        self.prompt_config = self.config.get("prompt", {})
        self.biz_scene = self.prompt_config.get("biz_scene") or os.getenv(
            "KAG_PROMPT_BIZ_SCENE", "default"
        )
        self.language = self.prompt_config.get("language") or os.getenv(
            "KAG_PROMPT_LANGUAGE", "zh"
        )
        self.table_keywords_prompt = PromptOp.load(self.biz_scene, "table_keywords")(
            language=self.language, project_id=self.project_id
        )
        self.kag_extractor = KAGExtractor(**kwargs)

    @property
    def input_types(self) -> Input:
        return Chunk

    @property
    def output_types(self) -> Output:
        return SubGraph

    def invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        invoke
        """
        input_table: Chunk = input
        table_type = input_table.kwargs["table_type"]
        if table_type in ["指标型表格", "Metric_Based_Table"]:
            return self._extract_metric_table(input_table)
        elif table_type in ["简单表格", "Simple_Table"]:
            return self._extract_simple_table(input_table)
        else:
            return self._extract_other_table(input_table)

    def _extract_metric_table(self, input_table: Chunk):
        table_info = input_table.kwargs["table_info"]
        header = table_info["header"]
        index_col = table_info["index_col"]
        table_df = self._std_table(
            input_table=input_table, header=header, index_col=index_col
        )
        table_name = table_info["name"]
        cell_describe_dict, keyword_dict, value_dict = (
            self._generate_metric_table_description(
                data=table_df,
                header=header,
                top_header_nonexist_flag=False,
                table_name=table_name,
            )
        )
        scale = table_info.get("sacle", None)
        unit = table_info.get("unit", None)
        table_global_keywords = input_table.kwargs["keywords"]
        keywords_and_colloquial_expression = self._extract_keyword_from_table_header(
            keyword_dict=keyword_dict, table_name=table_name
        )
        return self.get_subgraph(
            input_table,
            table_df,
            cell_describe_dict,
            keyword_dict,
            value_dict,
            table_global_keywords,
            scale,
            unit,
            keywords_and_colloquial_expression,
        )

    def _extract_keyword_from_table_header(self, keyword_dict: dict, table_name: str):
        keyword_list = set()
        for _, v in keyword_dict.items():
            keyword_list.update(v)
        context = table_name
        keyword_list = list(keyword_list)
        keyword_list.sort()
        input_dict = {"key_list": keyword_list, "context": context}
        keywords_and_colloquial_expression = self.llm.invoke(
            {
                "input": json.dumps(input_dict, ensure_ascii=False, sort_keys=True),
            },
            self.table_keywords_prompt,
            with_json_parse=True,
            with_except=True,
        )
        return keywords_and_colloquial_expression

    def _extract_simple_table(self, input_table: Chunk):
        rst = []
        if "table_info" in input_table.kwargs:
            table_info = input_table.kwargs["table_info"]
        else:
            table_info = {}
        if "header" in table_info and "index_col" in table_info:
            header = table_info["header"]
            index_col = table_info["index_col"]
            self._std_table(input_table=input_table, header=header, index_col=index_col)
        # 调用ner进行实体识别
        table_chunks = self.split_table(input_table, 500)
        for c in table_chunks:
            subgraph_lsit = self.kag_extractor.invoke(input=c)
            rst.extend(subgraph_lsit)
        return rst

    def _extract_other_table(self, input_table: Chunk):
        return self._extract_simple_table(input_table=input_table)

    def _std_table(self, input_table: Chunk, header: List, index_col: List):
        """
        按照表格新识别的表头，生成markdown文本
        """
        if "html" in input_table.kwargs:
            html = input_table.kwargs["html"]
            try:
                if len(header) <= 0:
                    header = None
                if not index_col or len(index_col) <= 0:
                    index_col = None
                table_df = pd.read_html(
                    StringIO(html),
                    header=header,
                    index_col=index_col,
                )[0]
            except IndexError:
                logging.exception("read html errro")
            table_df = table_df.astype(str)
            table_df = table_df.fillna("")
            input_table.content = table_df.to_markdown()
            del input_table.kwargs["html"]
            input_table.kwargs["content_type"] = "markdown"
            input_table.kwargs["csv"] = table_df.to_csv()
            return table_df

    def get_subgraph(
        self,
        input_table,
        table_df,
        cell_describe_dict,
        keyword_dict,
        value_dict,
        table_global_keywords,
        scale,
        unit,
        keywords_and_colloquial_expression,
    ):
        nodes = []
        edges = []

        # Table node
        table_desc = input_table.kwargs["context"]
        table_info = input_table.kwargs["table_info"]
        table_name = table_info["name"]
        table_node = Node(
            _id=input_table.id,
            name=table_name,
            label="Table",
            properties={
                "content": input_table.content,
                "csv": table_df.to_csv(),
                "desc": table_desc,
            },
        )
        nodes.append(table_node)

        all_keywords = {}

        for k, cell in cell_describe_dict.items():
            keywords_map = {kw: "local" for kw in keyword_dict[k]}
            for kw in table_global_keywords:
                keywords_map[kw] = "global"
            cell_value = value_dict[k]
            metric_id = f"{input_table.id}_{k}"
            metric = Node(
                _id=metric_id,
                name=cell,
                label="TableMetric",
                properties={
                    "value": cell_value,
                    "scale": scale,
                    "unit": unit,
                },
            )
            nodes.append(metric)

            # mertic to table
            edge = Edge(
                _id="m2t_" + metric_id,
                from_node=metric,
                to_node=table_node,
                label="source",
                properties={},
            )
            edges.append(edge)

            for keyword, _type in keywords_map.items():
                edge_id = f"{input_table.id}_{k}_{keyword}"
                keyword = keyword.lower()
                if keyword not in all_keywords:
                    keyword_node = Node(
                        _id=f"{table_name}_{keyword}",
                        name=keyword,
                        label="MetricConstraint",
                        properties={"type": _type},
                    )
                    all_keywords[keyword] = keyword_node
                    nodes.append(keyword_node)
                else:
                    keyword_node = all_keywords[keyword]
                # keywrod to metric
                edge = Edge(
                    _id="k2m_" + edge_id,
                    from_node=keyword_node,
                    to_node=metric,
                    label="dimension",
                    properties={},
                )
                edges.append(edge)

        for k, keyword_node in all_keywords.items():
            # keyword to table
            edge_id = f"e_{input_table.id}_{k}"
            edge = Edge(
                _id=edge_id,
                from_node=keyword_node,
                to_node=table_node,
                label="source",
                properties={},
            )
            edges.append(edge)

            # keyword and colloquial expression
            if k in keywords_and_colloquial_expression:
                colloquial: dict = keywords_and_colloquial_expression[k]
                for k_split, colloquial_list in colloquial.items():
                    k_split_node = Node(
                        _id=f"{table_name}_{k_split}",
                        name=k_split,
                        label="MetricConstraint",
                        properties={"type": "ks"},
                    )
                    nodes.append(k_split_node)
                    edge_id = f"ks_{input_table.id}_{k_split}"
                    edge = Edge(
                        _id=edge_id,
                        from_node=k_split_node,
                        to_node=keyword_node,
                        label="source",
                        properties={},
                    )
                    edges.append(edge)
                    for coll in colloquial_list:
                        k_coll_node = Node(
                            _id=f"{table_name}_{coll}",
                            name=coll,
                            label="MetricConstraint",
                            properties={"type": "ks_coll"},
                        )
                        nodes.append(k_coll_node)
                        edge_id = f"ks_coll_{input_table.id}_{coll}"
                        edge = Edge(
                            _id=edge_id,
                            from_node=k_coll_node,
                            to_node=keyword_node,
                            label="source",
                            properties={},
                        )
                        edges.append(edge)

        subgraph = SubGraph(nodes=nodes, edges=edges)
        return [subgraph]

    def _generate_metric_table_description(
        self,
        data: pd.DataFrame,
        header,
        top_header_nonexist_flag,
        table_name,
    ):
        describe_dict = {}
        value_dict = {}
        keyword_dict = {}
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = data.iloc[i, j]
                if (
                    str(value).startswith("Unnamed")
                    or str(value) == ""
                    or str(value) == "-"
                    or str(value) == "\u2014"
                ):
                    continue
                describe = ""
                keywords = set()
                if pd.isnull(data.index[i]):
                    describe += "total"
                    keywords.add("total")
                else:
                    describe += f"{data.index[i]}"
                    keywords.add(f"{data.index[i]}")
                temp_i = i - 1
                while temp_i >= 0:
                    if (data.iloc[temp_i] == "").all():
                        describe += f" {data.index[temp_i]}"
                        keywords.add(f"{data.index[temp_i]}")
                        break
                    temp_i -= 1
                if not top_header_nonexist_flag:
                    describe += " of"
                    if len(header) == 0:
                        pass
                    elif len(header) == 1:
                        header_str = self._handle_unnamed_single_topheader(
                            data.columns, j
                        )
                        describe += f" {header_str}"
                        keywords.add(header_str)
                    else:
                        header_str = self._handle_unnamed_multi_topheader(
                            data.columns, j
                        )
                        describe += f" {header_str}"
                        keywords.add(header_str)
                        prev = self._handle_unnamed_multi_topheader(data.columns, j)
                        for temp_j in header[1:]:
                            if (
                                data.columns[j][temp_j].startswith("Unnamed")
                                or data.columns[j][temp_j] == ""
                            ):
                                continue
                            if data.columns[j][temp_j] == prev:
                                continue
                            describe += f" {data.columns[j][temp_j]}"
                            keywords.add(f"{data.columns[j][temp_j]}")
                            prev = data.columns[j][temp_j]
                describe += f" is {data.iloc[i, j]}."
                x_index = i + len(header)
                y_index = j + 1
                if top_header_nonexist_flag == 1:
                    x_index -= 1
                describe_dict[f"{x_index}-{y_index}"] = (
                    f"[{table_name}][{x_index}-{y_index}]shows: {describe}"
                )
                value_dict[f"{x_index}-{y_index}"] = f"{data.iloc[i, j]}"
                keyword_dict[f"{x_index}-{y_index}"] = keywords
        return describe_dict, keyword_dict, value_dict

    def _handle_unnamed_single_topheader(self, columns, j):
        tmp = j
        while tmp < len(columns) and (
            columns[tmp].startswith("Unnamed") or columns[tmp] == ""
        ):
            tmp += 1
        if tmp < len(columns):
            return columns[tmp]

        tmp = j
        while tmp >= 0 and (columns[tmp].startswith("Unnamed") or columns[tmp] == ""):
            tmp -= 1
        if tmp < 0:
            return f"data {j}"
        else:
            return columns[tmp]

    def _handle_unnamed_multi_topheader(self, columns, j):
        tmp = j
        while tmp < len(columns) and (
            columns[tmp][0].startswith("Unnamed") or columns[tmp][0] == ""
        ):
            tmp += 1
        if tmp < len(columns):
            return columns[tmp][0]

        tmp = j
        while tmp >= 0 and (
            columns[tmp][0].startswith("Unnamed") or columns[tmp][0] == ""
        ):
            tmp -= 1
        if tmp < 0:
            return f"data {j}"
        else:
            return columns[tmp][0]
