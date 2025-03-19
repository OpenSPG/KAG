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
import markdown
from bs4 import BeautifulSoup, Tag
from typing import List, Set, Dict


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
from kag.builder.component.extractor.text_extractor import TextExtractor
from kag.builder.component.table.table_cell import TableCell, TableInfo
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
        self.table_keywords_prompt = PromptOp.load("table", "table_keywords")(
            language=self.language, project_id=self.project_id
        )
        self.table_reformat = PromptOp.load("table", "table_reformat")(
            language=self.language, project_id=self.project_id
        )
        self.text_extractor = TextExtractor(**kwargs)

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

        # return self._extract_metric_table(input_table)
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
        table_df, header, index_col = self._std_table2(input_table=input_table)
        table_name = input_table.kwargs["table_name"]
        cell_value_desc = None
        scale = table_info.get("scale", None)
        units = table_info.get("units", None)
        if scale is not None:
            cell_value_desc = str(scale)
        if units is not None and isinstance(units, str):
            cell_value_desc += "," + units
        if cell_value_desc is not None:
            cell_value_desc = "(" + cell_value_desc + ")"

        table_cell_info: TableInfo = self._generate_table_cell_info(
            data=table_df,
            header=header,
            table_name=table_name,
            cell_value_desc=cell_value_desc,
        )
        table_cell_info.sacle = table_info.get("scale", None)
        table_cell_info.unit = table_info.get("units", None)
        table_cell_info.context_keywords = input_table.kwargs["keywords"]
        keyword_set = set()
        keyword_set.add(table_name)
        for table_cell in table_cell_info.cell_dict.values():
            table_cell: TableCell = table_cell
            keyword_set.update(list(table_cell.row_keywords.keys()))
        keywords_and_colloquial_expression = self._extract_keyword_from_table_header(
            keyword_set=keyword_set, table_name=table_name
        )
        for k, v in keywords_and_colloquial_expression.items():
            if k == table_name:
                table_cell_info.table_name_colloquial = v
                continue
            for table_cell in table_cell_info.cell_dict.values():
                if k in table_cell.row_keywords:
                    table_cell.row_keywords[k] = v
        return self.get_subgraph(
            input_table,
            table_df,
            table_cell_info,
        )

    def _extract_keyword_from_table_header(self, keyword_set: Set, table_name: str):
        context = table_name
        keyword_list = list(keyword_set)
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
            table_info = input_table.kwargs.pop("table_info")
        else:
            table_info = {}
        if "header" in table_info and "index_col" in table_info:
            header = table_info["header"]
            index_col = table_info["index_col"]
            self._std_table(input_table=input_table, header=header, index_col=index_col)
        # 调用ner进行实体识别
        table_chunks = self.split_table(input_table, 500)
        for c in table_chunks:
            subgraph_lsit = self.text_extractor.invoke(input=c)
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
            table_df = table_df.fillna("")
            table_df = table_df.astype(str)
            input_table.content = table_df.to_markdown()
            del input_table.kwargs["html"]
            input_table.kwargs["content_type"] = "markdown"
            input_table.kwargs["csv"] = table_df.to_csv()
            return table_df, header, index_col

    def _std_table2(self, input_table: Chunk):
        """
        转换表格
        使用大模型转换
        """
        input_str = input_table.content
        # skip table reformat
        new_markdown = self.llm.invoke(
            {"input": input_str}, self.table_reformat, with_except=True
        )
        # new_markdown = input_str
        # new_markdown = new_markdown.replace("&nbsp;&nbsp;", "-")

        html_content = markdown.markdown(
            new_markdown, extensions=["markdown.extensions.tables"]
        )
        try:
            table_df = pd.read_html(StringIO(html_content), header=[0], index_col=[0])[
                0
            ]
        except ValueError:
            # 可能是表头数量没对齐，再尝试一次
            new_markdown = self._fix_llm_markdown(llm_markdown=new_markdown)
            html_content = markdown.markdown(
                new_markdown, extensions=["markdown.extensions.tables"]
            )
            table_df = pd.read_html(StringIO(html_content), header=[0], index_col=[0])[
                0
            ]

        table_df = table_df.fillna("")
        table_df = table_df.astype(str)
        input_table.content = table_df.to_markdown()
        input_table.kwargs.pop("html", None)
        input_table.kwargs["content_type"] = "markdown"
        input_table.kwargs["csv"] = table_df.to_csv()
        return table_df, [0], [0]

    def _fix_llm_markdown(self, llm_markdown: str):
        # 将输入的表格按行分割
        lines = llm_markdown.strip().split("\n")

        # 获取表头
        header = lines[0].strip()

        # 获取分隔行并根据 '|' 分割
        separator = lines[1].strip().split("|")

        # 确保 header 和每行都有前后的 '|'
        if not header.startswith("|"):
            header = "|" + header
        if not header.endswith("|"):
            header = header + "|"

        # 获取列数
        num_columns = header.count("|") - 1

        # 修复分隔行
        fixed_separator = "|" + "|".join(["---"] * num_columns) + "|"

        # 创建修复后的表格
        fixed_lines = [header, fixed_separator] + lines[2:]

        # 返回修复后的表格
        return "\n".join(fixed_lines)

    # def get_subgraph(
    #     self, input_table: Chunk, table_df: pd.DataFrame, table_cell_info: TableInfo
    # ):
    #     nodes = []
    #     edges = []
    #     print(f"input_table = {input_table.content}")
    #     print(f"table_df = {table_df}")
    #     print(table_cell_info.cell_dict)
    #     table_id = input_table.id

    #     # Table node
    #     table_desc = input_table.kwargs["context"]
    #     table_name = input_table.kwargs["table_name"]
    #     table_node = Node(
    #         _id=table_id,
    #         name=table_name,
    #         label="Table",
    #         properties={
    #             "content": input_table.content,
    #             "csv": table_df.to_csv(),
    #             "desc": table_desc,
    #         },
    #     )
    #     nodes.append(table_node)

    #     # all cell node
    #     for k, cell in table_cell_info.cell_dict.items():
    #         table_cell: TableCell = cell
    #         cell_id = f"{table_id}_{k}"
    #         # cell node
    #         metric = Node(
    #             _id=cell_id,
    #             name=table_cell.desc,
    #             label="TableMetric",
    #             properties={
    #                 "value": table_cell.value,
    #                 "scale": table_cell_info.sacle,
    #                 "unit": table_cell_info.unit,
    #             },
    #         )
    #         nodes.append(metric)

    #         # cell to table
    #         edge = Edge(
    #             _id="c2t_" + cell_id,
    #             from_node=metric,
    #             to_node=table_node,
    #             label="source",
    #             properties={},
    #         )
    #         edges.append(edge)

    #         all_keywords_dict = {}

    #         # all table global keywords
    #         global_keywords = input_table.kwargs.get("keywords", [])
    #         for gk in global_keywords:
    #             global_keyword: str = gk
    #             keyword_id = f"{table_name}_{global_keyword}"
    #             if keyword_id in all_keywords_dict:
    #                 continue
    #             keyword_node = Node(
    #                 _id=keyword_id,
    #                 name=global_keyword,
    #                 label="MetricConstraint",
    #                 properties={"type": "global"},
    #             )
    #             all_keywords_dict[keyword_id] = keyword_node
    #             nodes.append(keyword_node)

    #             # keywrod to metric
    #             edge = Edge(
    #                 _id="gk2c_" + keyword_id,
    #                 from_node=keyword_node,
    #                 to_node=metric,
    #                 label="dimension",
    #                 properties={},
    #             )
    #             edges.append(edge)

    #         # all row_keywords
    #         for rk, rv in table_cell.row_keywords.items():
    #             row_keyword: str = rk
    #             keyword_id = f"{table_name}_{row_keyword}"
    #             if keyword_id in all_keywords_dict:
    #                 continue
    #             keyword_node = Node(
    #                 _id=keyword_id,
    #                 name=row_keyword,
    #                 label="MetricConstraint",
    #                 properties={"type": "row"},
    #             )
    #             all_keywords_dict[keyword_id] = keyword_node
    #             nodes.append(keyword_node)

    #             # keywrod to metric
    #             edge = Edge(
    #                 _id="k2c_" + keyword_id,
    #                 from_node=keyword_node,
    #                 to_node=metric,
    #                 label="dimension",
    #                 properties={},
    #             )
    #             edges.append(edge)

    #             # all splited keywords
    #             for sk, sv in rv.items():
    #                 splited_keyword: str = sk
    #                 s_keyword_id = f"{table_name}_{splited_keyword}"
    #                 if s_keyword_id in all_keywords_dict:
    #                     splited_keyword_node = all_keywords_dict[s_keyword_id]
    #                     c_nodes, c_edges = self._get_colloquial_nodes_and_edges(
    #                         colloquial_list=sv,
    #                         table_name=table_name,
    #                         all_keywords_dict=all_keywords_dict,
    #                         splited_keyword_node=splited_keyword_node,
    #                     )
    #                     nodes.extend(c_nodes)
    #                     edges.extend(c_edges)
    #                     continue
    #                 splited_keyword_node = Node(
    #                     _id=s_keyword_id,
    #                     name=splited_keyword,
    #                     label="MetricConstraint",
    #                     properties={"type": "splited"},
    #                 )
    #                 all_keywords_dict[s_keyword_id] = splited_keyword_node
    #                 nodes.append(splited_keyword_node)

    #                 # keyword to row_keyword
    #                 edge = Edge(
    #                     _id="k2rk_" + s_keyword_id,
    #                     from_node=splited_keyword_node,
    #                     to_node=keyword_node,
    #                     label="parent",
    #                     properties={},
    #                 )
    #                 edges.append(edge)

    #                 c_nodes, c_edges = self._get_colloquial_nodes_and_edges(
    #                     colloquial_list=sv,
    #                     table_name=table_name,
    #                     all_keywords_dict=all_keywords_dict,
    #                     splited_keyword_node=splited_keyword_node,
    #                 )
    #                 nodes.extend(c_nodes)
    #                 edges.extend(c_edges)
    #     subgraph = SubGraph(nodes=nodes, edges=edges)
    #     return [subgraph]

    def get_subgraph(
        self, input_table: Chunk, table_df: pd.DataFrame, table_cell_info: TableInfo
    ):
        nodes = []
        edges = []
        import pickle

        # with open("table_data.pkl", "wb") as f:
        #     pickle.dump((input_table, table_df, table_cell_info), f)
        # print("write to table_data.pkl")

        table_id = input_table.id

        # keywords node
        keyword_str_set = set(table_cell_info.context_keywords)
        keywords = []

        for k, cell in table_cell_info.cell_dict.items():
            keyword_str_set = keyword_str_set.union(set(cell.row_keywords.keys()))

        for keyword in keyword_str_set:
            node = Node(
                _id=f"{table_id}-keyword{keyword}",
                name=keyword,
                label="TableKeyWord",
                properties={},
            )
            keywords.append(node.id)
            nodes.append(node)
        # Table node
        table_desc = input_table.kwargs["context"]
        table_name = input_table.kwargs["table_name"]
        table_node = Node(
            _id=table_id,
            name=table_name,
            label="Table",
            properties={
                "raw_name": table_name,
                "content": input_table.content,
                "csv": table_df.to_csv(),
                "desc": table_desc,
            },
        )
        nodes.append(table_node)

        # TableRow nodes
        idx = 0
        rows = {}
        levels = []
        for row_name, row_value in table_df.iterrows():
            node = Node(
                _id=f"{table_id}-row-{idx}",
                name=f"{table_name}-{row_name.lstrip('-').strip()}",
                label="TableRow",
                properties={
                    "raw_name": row_name.lstrip("-").strip(),
                    "content": row_value.to_csv(),
                    "desc": table_desc,
                },
            )
            rows[idx] = (row_name.lstrip("-").strip(), node.id)
            row_level = 0
            for c in row_name:
                if c != "-":
                    break
                else:
                    row_level += 1
            levels.append((idx, row_level, node.id))
            idx += 1
            nodes.append(node)
        # TableCol nodes
        idx = 0
        cols = {}
        for col_name, col_value in table_df.items():
            node = Node(
                _id=f"{table_id}-col-{idx}",
                name=f"{table_name}-{col_name}",
                label="TableColumn",
                properties={
                    "raw_name": col_name,
                    "content": col_value.to_csv(),
                    "desc": table_desc,
                },
            )
            cols[idx] = (col_name, node.id)
            idx += 1
            nodes.append(node)

        # Table cells
        cells = {}
        for k, cell in table_cell_info.cell_dict.items():
            row_num, col_num = k.split("-")
            row_num = int(row_num)
            col_num = int(col_num)
            row_name, _ = rows[row_num]
            col_name, _ = cols[col_num]
            table_cell: TableCell = cell
            cell_id = f"{table_id}-{k}"
            # cell node
            node = Node(
                _id=cell_id,
                name=f"{table_name}-{row_name}-{col_name}",
                label="TableCell",
                properties={
                    "raw_name": f"{row_name}-{col_name}",
                    "row_name": row_name,
                    "col_name": col_name,
                    "desc": table_cell.desc,
                    "value": table_cell.value,
                    "scale": table_cell_info.sacle,
                    "unit": table_cell_info.unit,
                },
            )
            cells[(row_num, col_num)] = node.id
            nodes.append(node)
        node_map = {}
        for node in nodes:
            node_map[node.id] = node
        # table <-> row
        for k, v in rows.items():
            row_name, row_id = v
            edge = Edge(
                _id=f"table-{table_id}-col-{row_id}",
                from_node=node_map[table_id],
                to_node=node_map[row_id],
                label="containRow",
                properties={},
            )

            edges.append(edge)

            edge = Edge(
                _id=f"row-{row_id}-table-{table_id}",
                from_node=node_map[row_id],
                to_node=node_map[table_id],
                label="partOf",
                properties={},
            )
            edges.append(edge)

        # table <-> col
        for k, v in cols.items():
            col_name, col_id = v
            edge = Edge(
                _id=f"table-{table_id}-col-{col_id}",
                from_node=node_map[table_id],
                to_node=node_map[col_id],
                label="containColumn",
                properties={},
            )
            edges.append(edge)

            edge = Edge(
                _id=f"col-{col_id}-table-{table_id}",
                from_node=node_map[col_id],
                to_node=node_map[table_id],
                label="partOf",
                properties={},
            )
            edges.append(edge)

        # table/row/col <-> table cell
        for cell_loc, cell_id in cells.items():
            row_num, col_num = cell_loc
            row_id = rows[row_num][1]
            col_id = cols[col_num][1]
            edge = Edge(
                _id=f"row-{row_id}-contain-cell-{cell_id}",
                from_node=node_map[row_id],
                to_node=node_map[cell_id],
                label="containCell",
                properties={},
            )
            edges.append(edge)
            edge = Edge(
                _id=f"cell-{cell_id}-part-of-row-{row_id}",
                from_node=node_map[cell_id],
                to_node=node_map[row_id],
                label="partOfTableRow",
                properties={},
            )
            edges.append(edge)

            edge = Edge(
                _id=f"col-{col_id}-contain_cell-{cell_id}",
                from_node=node_map[col_id],
                to_node=node_map[cell_id],
                label="containCell",
                properties={},
            )
            edges.append(edge)
            edge = Edge(
                _id=f"cell-{cell_id}-part-of-col-{col_id}",
                from_node=node_map[cell_id],
                to_node=node_map[col_id],
                label="partOfTableColumn",
                properties={},
            )
            edges.append(edge)

            edge = Edge(
                _id=f"cell-{cell_id}-part-of-table-{table_id}",
                from_node=node_map[cell_id],
                to_node=node_map[col_id],
                label="partOfTable",
                properties={},
            )

        # row subitem
        for i in range(len(levels)):
            # row_num = levels[i][0]
            # row_info = levels[i][1]
            row_num, row_level, row_id = levels[i]
            if row_level != 0:
                for j in range(i - 1, -1, -1):
                    tmp_row_num, tmp_row_level, tmp_row_id = levels[j]
                    # tmp_row_info = levels[j][1]

                    # tmp_row_level, tmp_row_id = tmp_row_info
                    if tmp_row_level < row_level:
                        edge = Edge(
                            _id=f"row-{row_id}-sub-item-{tmp_row_id}",
                            from_node=node_map[tmp_row_id],
                            to_node=node_map[row_id],
                            label="subitem",
                            properties={},
                        )
                        edges.append(edge)
                        break

        # table ->keyword
        for keyword_id in keywords:
            edge = Edge(
                _id=f"keyword-{keyword_id}-table-{table_id}",
                from_node=node_map[keyword_id],
                to_node=node_map[table_id],
                label="keyword",
                properties={},
            )
            edges.append(edge)

        subgraph = SubGraph(nodes=nodes, edges=edges)
        print("*" * 80)
        print(
            f"done process {table_df.shape} table to subgraph with {len(nodes)} nodes and {len(edges)} edges"
        )
        print(f"node stat: {self.stat(nodes)}")
        print(f"edge stat: {self.stat(edges)}")
        return [subgraph]

    def stat(self, items):
        out = {}
        for item in items:
            label = item.label
            if label in out:
                out[label] += 1
            else:
                out[label] = 1
        return out

    def _get_colloquial_nodes_and_edges(
        self,
        colloquial_list: List,
        table_name: str,
        all_keywords_dict: Dict,
        splited_keyword_node: Node,
    ):
        nodes = []
        edges = []
        for ck in colloquial_list:
            colloquial_keyword: str = ck
            c_keyword_id = f"{table_name}_{colloquial_keyword}"
            if c_keyword_id in all_keywords_dict:
                continue
            c_keyword_node = Node(
                _id=c_keyword_id,
                name=colloquial_keyword,
                label="MetricConstraint",
                properties={"type": "colloquial"},
            )
            all_keywords_dict[c_keyword_id] = c_keyword_node
            nodes.append(c_keyword_node)

            # keyword to row_keyword
            edge = Edge(
                _id="k2rk2c_" + c_keyword_id,
                from_node=c_keyword_node,
                to_node=splited_keyword_node,
                label="colloquial",
                properties={},
            )
            edges.append(edge)
        return nodes, edges

    def _generate_table_cell_info(
        self,
        data: pd.DataFrame,
        header,
        table_name,
        cell_value_desc,
    ):
        table_info = TableInfo(table_name=table_name)
        sub_item_dict = {}

        def format_value(value):
            value = value.replace("(", "").replace(")", "").replace(",", "")
            if value.endswith("%"):
                # 去除百分号并转换为浮点数
                return float(value.rstrip("%")) / 100
            elif value.isdigit():
                return float(value)
            else:
                return None

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = data.iloc[i, j]
                #value = format_value(value)
                #if not value:
                #    continue
                x_index = i + len(header)
                y_index = j + 1
                cell_id = f"{x_index-1}-{y_index-1}"
                row_keywords = {}
                describe = ""
                now_index_str = None
                if pd.isnull(data.index[i]):
                    describe += "total"
                    row_keywords["total"] = {}
                else:
                    now_index_str = f"{data.index[i]}"
                    describe += now_index_str
                    row_keywords[now_index_str] = {}
                temp_i = i - 1
                while temp_i >= 0:
                    if (data.iloc[temp_i] == "").all():
                        parent_str = f"{data.index[temp_i]}"
                        parent_str = parent_str.strip(":").strip("：")
                        describe += f" in {parent_str}"
                        row_keywords[parent_str] = {}
                        if now_index_str is not None:
                            sub_item_set = sub_item_dict.get(parent_str, set())
                            sub_item_set.add(now_index_str)
                            sub_item_dict[parent_str] = sub_item_set
                        break
                    temp_i -= 1

                describe += " of"
                if len(header) == 0:
                    pass
                elif len(header) == 1:
                    header_str = self._handle_unnamed_single_topheader(data.columns, j)
                    describe += f" {header_str}"
                    row_keywords[header_str] = {}
                else:
                    header_str = self._handle_unnamed_multi_topheader(data.columns, j)
                    describe += f" {header_str}"
                    row_keywords[header_str] = {}
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
                        row_keywords[f"{data.columns[j][temp_j]}"] = {}
                        prev = data.columns[j][temp_j]
                describe += f" is {data.iloc[i, j]}{cell_value_desc}"
                describe = f"[{table_name}]cell[{cell_id}] shows " + describe
                table_cell = TableCell(desc=describe, row_keywords=row_keywords)
                table_cell.value = data.iloc[i, j]
                table_info.cell_dict[cell_id] = table_cell
        table_info.sub_item_dict = sub_item_dict
        return table_info

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
