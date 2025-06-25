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

import logging
from io import StringIO
from typing import Type, List

from kag.common.conf import KAG_CONFIG
import markdown
import pandas as pd
from tenacity import stop_after_attempt, retry

from kag.interface import LLMClient
from kag.interface import ExtractorABC, PromptABC, ExternalGraphLoaderABC
from kag.common.utils import generate_hash_id
from knext.common.base.runnable import Input, Output
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.component.extractor.schema_free_extractor import SchemaFreeExtractor
from kag.builder.model.sub_graph import SubGraph, Node, Edge
from kag.examples.finqa.builder.table_model import (
    TableDefaultInfo,
    TableRowSummary,
    TableColSummary,
)


from kag.examples.finqa.builder.prompt.table_context import TableContextPrompt
from kag.examples.finqa.builder.prompt.table_row_col_summary import (
    TableRowColSummaryPrompt,
)

__all__ = ["TableContextPrompt", "TableRowColSummaryPrompt"]

logger = logging.getLogger(__name__)


@ExtractorABC.register("table_and_text_extractor")
class TableAndTextExtractor(ExtractorABC):
    """
    A class for extracting knowledge graph subgraphs from table and text using a large language model (LLM).
    Inherits from the Extractor base class.

    Attributes:
        llm (LLMClient): The large language model client used for text processing.
        ner_prompt (PromptABC): The prompt used for named entity recognition.
        std_prompt (PromptABC): The prompt used for named entity standardization.
        triple_prompt (PromptABC): The prompt used for triple extraction.
        external_graph (ExternalGraphLoaderABC): The external graph loader used for additional NER.
    """

    def __init__(
        self,
        llm: LLMClient,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        triple_prompt: PromptABC = None,
        table_context_prompt: PromptABC = None,
        table_row_col_summary_prompt: PromptABC = None,
        external_graph: ExternalGraphLoaderABC = None,
    ):
        """
        Initializes the KAGExtractor with the specified parameters.

        Args:
            llm (LLMClient): The large language model client.
            ner_prompt (PromptABC, optional): The prompt for named entity recognition. Defaults to None.
            std_prompt (PromptABC, optional): The prompt for named entity standardization. Defaults to None.
            triple_prompt (PromptABC, optional): The prompt for triple extraction. Defaults to None.
            external_graph (ExternalGraphLoaderABC, optional): The external graph loader. Defaults to None.
        """
        super().__init__()
        self.schema_free_extractor = SchemaFreeExtractor(
            llm, ner_prompt, std_prompt, triple_prompt, external_graph
        )
        self.llm = llm
        self.table_context_prompt = table_context_prompt
        self.table_row_col_summary_prompt = table_row_col_summary_prompt
        self.split_table_to_chunk = True

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        table_chunk: Chunk = input
        if table_chunk.type == ChunkTypeEnum.Table:
            return self._invoke_table(input, **kwargs)
        return self.schema_free_extractor._invoke(input, **kwargs)

    @retry(stop=stop_after_attempt(3))
    def _invoke_table(self, input: Chunk, **kwargs) -> List[Output]:
        try:
            input.id = generate_hash_id(input.content)
            self._table_context(input)
            return self._table_extractor(input)
        except:
            logger.debug(f"_invoke_table failed for chunk:{input}")
            try:
                return self._raw_table_extractor(input)
            except:
                logger.exception(f"_invoke_table failed for chunk:{input}")
                raise RuntimeError(f"table extract failed for chunk:{input}")

    def _table_extractor(self, input_table: Chunk):
        html_content = markdown.markdown(
            input_table.content, extensions=["markdown.extensions.tables"]
        )
        table_df = pd.read_html(StringIO(html_content))[0]
        row_summary_list, col_summary_list = self._get_row_col_summary_by_llm(
            input_table=input_table, table_df=table_df
        )

        if self.split_table_to_chunk:
            rst_list = []
            chunks = self._do_split_table_to_chunk(
                input_table=input_table,
                row_summary_list=row_summary_list,
                col_summary_list=col_summary_list,
            )
            sub_graph = SubGraph(nodes=[], edges=[])
            for chunk in chunks:
                sub_graph.add_node(
                    chunk.id,
                    chunk.name,
                    "Chunk",
                    {
                        "id": chunk.id,
                        "name": chunk.name,
                        "content": f"{chunk.name}\n{chunk.content}",
                        **chunk.kwargs,
                    },
                )
                rst_list.append(sub_graph)
                # subgraphs = self.schema_free_extractor._invoke(chunk)
                # rst_list.extend(subgraphs)
            return rst_list
        subgraph = self._gen_subgraph(
            input_table=input_table,
            table_df=table_df,
            row_summary_list=row_summary_list,
            col_summary_list=col_summary_list,
        )
        return [subgraph]

    def _raw_table_extractor(self, input_table: Chunk):
        table_id = input_table.id
        table_info: TableDefaultInfo = input_table.kwargs.get("table_info", None)
        table_desc = ""
        table_name = f"table_{table_id}"
        if table_info is not None:
            table_desc = table_info.desc
            table_name = table_info.name
        content = table_desc + "\n" + input_table.content
        chunk = Chunk(
            id=f"table_{table_id}",
            name=table_name,
            content=content,
            type=ChunkTypeEnum.Text,
        )
        subgraphs = self.schema_free_extractor._invoke(chunk)
        return subgraphs

    def _do_split_table_to_chunk(
        self,
        input_table: Chunk,
        row_summary_list: list[TableRowSummary],
        col_summary_list: list[TableColSummary],
    ):
        doc_name = input_table.kwargs.get("file_name", "unknow doc name")
        table_id = input_table.id
        table_info: TableDefaultInfo = input_table.kwargs.get("table_info", None)
        table_name = table_info.name
        rst_chunk_list = []

        # table chunk
        chunk = Chunk(
            id=f"table_{table_id}",
            name=f"{doc_name} / {table_name} / {table_info.desc}",
            content=input_table.content,
            type=ChunkTypeEnum.Text,
        )
        rst_chunk_list.append(chunk)

        # TableRow nodes
        if len(row_summary_list) > 1:
            for i, row_summary in enumerate(row_summary_list):
                # content = f"doc: {doc_name}\ntable: {table_name}\ntable_row_summary: {row_summary.summary}\n{row_summary.content}"
                content = row_summary.content
                chunk = Chunk(
                    id=f"table_{table_id}_row_{i}",
                    name=f"{doc_name} / {table_name} / {row_summary.summary}",
                    content=content,
                    type=ChunkTypeEnum.Text,
                )
                rst_chunk_list.append(chunk)
        # TableColumn nodes
        if len(col_summary_list) > 1:
            for i, col_summary in enumerate(col_summary_list):
                # content = f"doc: {doc_name}\ntable: {table_name}\ntable_column_summary: {col_summary.summary}\n{col_summary.content}"
                content = col_summary.content
                chunk = Chunk(
                    id=f"table_{table_id}_col_{i}",
                    name=f"{doc_name} / {table_name} / {col_summary.summary}",
                    content=content,
                    type=ChunkTypeEnum.Text,
                )
                rst_chunk_list.append(chunk)
        return rst_chunk_list

    def _table_context(self, input_table: Chunk):
        # 提取全局信息
        table_context_str = self._get_table_context_str(table_chunk=input_table)
        table_info = self.llm.invoke(
            {
                "input": table_context_str,
            },
            self.table_context_prompt,
            with_json_parse=True,
            with_except=True,
        )
        table_name = table_info["table_name"]
        table_desc = table_info["table_desc"]
        table_keywords = table_info["keywords"]
        table_info = TableDefaultInfo(
            name=table_name,
            desc=table_desc,
            keywords=table_keywords,
        )
        input_table.kwargs["table_info"] = table_info
        return table_info

    def _get_table_context_str(self, table_chunk: Chunk):
        file_name = table_chunk.kwargs.get("file_name", "")
        section = table_chunk.name
        before_text = table_chunk.kwargs["metadata"].get("before_text", "")
        after_text = table_chunk.kwargs["metadata"].get("after_text", "")
        return (
            file_name
            + "\n"
            + section
            + "\n"
            + before_text
            + "\n"
            + table_chunk.content
            + "\n"
            + after_text
        )

    def _table_to_markdown(self, df):
        new_df = df.copy()
        new_df.insert(0, "row_index_0", [f"row_index_{i+1}" for i in range(len(new_df))])
        new_columns = []
        for i, c in enumerate(new_df.columns):
            if 0 == i:
                new_columns.append(c)
                continue
            new_columns.append(f"{c}[column{i-1}]")
        new_df.columns = new_columns
        return new_df

    def _get_row_col_summary_by_llm(self, input_table: Chunk, table_df: pd.DataFrame):
        table_info: TableDefaultInfo = input_table.kwargs["table_info"]
        table_desc = table_info.desc
        table_df_tmp = self._table_to_markdown(table_df)
        input_str = (
            "table summary: "
            + table_desc
            + "\n"
            + table_df_tmp.to_markdown(index=False)
        )
        llm: LLMClient = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
        row_col_summary_info = llm.invoke(
            variables={"input": input_str},
            prompt_op=self.table_row_col_summary_prompt,
            with_json_parse=True,
            with_except=True,
        )
        row_summary_list = row_col_summary_info["rows"]
        col_summary_list = row_col_summary_info["columns"]
        row_num, column_num = table_df.shape
        if len(row_summary_list) > row_num + 1 or len(row_summary_list) < row_num:
            return [], []
        if len(col_summary_list) != column_num:
            return [], []

        # 获取head_rows和index_cols
        if len(row_summary_list) == row_num + 1:
            with_head_summary = True
        else:
            with_head_summary = False

        header_list = list(table_df.columns)
        for row_summary in row_summary_list:
            if row_summary["type"] != "header":
                continue
            row_index = row_summary["index"]
            new_header_list = None
            if with_head_summary:
                if 0 == row_index:
                    continue
                else:
                    new_header_list = table_df.iloc[row_index - 1].tolist()
            else:
                new_header_list = table_df.iloc[row_index].tolist()
            if header_list is None:
                header_list = new_header_list
            else:
                header_list = zip(header_list, new_header_list)
        index_list = None
        for col_summary in col_summary_list:
            if col_summary["type"] != "index":
                continue
            col_index = col_summary["index"]
            col_name = table_df.columns[col_index]
            col_data = [col_name] + table_df.iloc[:, col_index].tolist()
            if index_list is None:
                index_list = col_data
            else:
                index_list = zip(index_list, col_data)
        if header_list is None or index_list is None:
            # 缺乏header和index
            raise RuntimeError("table no header or index")
        # get data
        rst_row_summary_list = []
        for row_summary in row_summary_list:
            if row_summary["type"] != "data":
                continue
            row_index = row_summary["index"]
            if with_head_summary:
                row_index -= 1
            data = table_df.iloc[row_index].tolist()
            df = pd.DataFrame([data], columns=header_list)
            content = df.to_markdown(index=False)
            rst_row_summary_list.append(
                TableRowSummary(summary=row_summary["summary"], content=content)
            )
        rst_col_summary_list = []
        for col_summary in col_summary_list:
            if col_summary["type"] != "data":
                continue
            col_index = col_summary["index"]
            col_name = table_df.columns[col_index]
            col_data = [col_name] + table_df.iloc[:, col_index].tolist()
            df = pd.DataFrame(col_data[1:], index=index_list[1:], columns=[col_data[0]])
            df.index.name = str(index_list[0])
            content = df.to_markdown(index=True)
            rst_col_summary_list.append(
                TableColSummary(summary=col_summary["summary"], content=content)
            )
        return rst_row_summary_list, rst_col_summary_list

    def _gen_subgraph(
        self,
        input_table: Chunk,
        table_df: pd.DataFrame,
        row_summary_list: list[TableRowSummary],
        col_summary_list: list[TableColSummary],
    ):
        """
        generate subgraph
        """
        nodes = []
        edges = []

        table_id = input_table.id

        table_info: TableDefaultInfo = input_table.kwargs.get("table_info", None)

        # Table node
        table_desc = table_info.desc
        table_name = table_info.name
        table_node = Node(
            _id=table_id,
            name=table_name,
            label="Table",
            properties={
                "content": input_table.content,
                "csv": table_df.to_csv() if table_df is not None else None,
                "desc": table_desc,
            },
        )
        nodes.append(table_node)

        # keywords node
        keyword_str_set = set(table_info.keywords)
        for keyword in keyword_str_set:
            keyword_id = f"{table_id}-keyword-{keyword}"
            node = Node(
                _id=keyword_id,
                name=keyword,
                label="TableKeyWord",
                properties={},
            )
            nodes.append(node)
            # keyword -> table
            edge = Edge(
                _id=f"keyword-{keyword}-table-{table_id}",
                from_node=node,
                to_node=table_node,
                label="keyword",
                properties={},
            )
            edges.append(edge)

        # TableRow nodes
        for i, row_summary in enumerate(row_summary_list):
            node = Node(
                _id=f"{table_id}-row-{i}",
                name=f"{table_name}-{row_summary.summary}",
                label="TableRow",
                properties={
                    "raw_name": row_summary.summary,
                    "content": row_summary.content,
                },
            )
            nodes.append(node)
        # TableColumn nodes
        for i, col_summary in enumerate(col_summary_list):
            node = Node(
                _id=f"{table_id}-column-{i}",
                name=f"{table_name}-{col_summary.summary}",
                label="TableColumn",
                properties={
                    "raw_name": col_summary.summary,
                    "content": col_summary.content,
                },
            )
            nodes.append(node)

        node_map = {}
        for node in nodes:
            node_map[node.id] = node

        # table <-> row
        for i, row_summary in enumerate(row_summary_list):
            row_id = f"{table_id}-row-{i}"
            edge = Edge(
                _id=f"table-{table_id}-row-{i}",
                from_node=node_map[table_id],
                to_node=node_map[row_id],
                label="containRow",
                properties={},
            )

            edges.append(edge)

            edge = Edge(
                _id=f"row-{i}-table-{table_id}",
                from_node=node_map[row_id],
                to_node=node_map[table_id],
                label="partOf",
                properties={},
            )
            edges.append(edge)

        # table <-> column
        for i, col_summary in enumerate(col_summary_list):
            col_id = f"{table_id}-column-{i}"
            edge = Edge(
                _id=f"table-{table_id}-col-{i}",
                from_node=node_map[table_id],
                to_node=node_map[col_id],
                label="containColumn",
                properties={},
            )
            edges.append(edge)

            edge = Edge(
                _id=f"col-{i}-table-{table_id}",
                from_node=node_map[col_id],
                to_node=node_map[table_id],
                label="partOf",
                properties={},
            )
            edges.append(edge)
        subgraph = SubGraph(nodes=nodes, edges=edges)
        return subgraph
