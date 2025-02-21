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
from kag.builder.component.table.table_model import (
    TableCellValue,
    TableCellDesc,
    TableDefaultInfo,
)


from kag.builder.prompt.table.table_context import TableContextPrompt
from kag.builder.prompt.table.table_row_col_summary import TableRowColSummaryPrompt

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
        matrix_table_index_prompt: PromptABC = None,
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
        self.matrix_table_index_prompt = matrix_table_index_prompt

    @property
    def input_types(self) -> Type[Input]:
        return Chunk

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the semantic extractor to process input data.

        Args:
            input (Input): Input data containing name and content.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: A list of processed results, containing subgraph information.
        """
        table_chunk: Chunk = input
        if table_chunk.type == ChunkTypeEnum.Table:
            return self._invoke_table(input, **kwargs)
        return []
        return self.schema_free_extractor._invoke(input, **kwargs)

    @retry(stop=stop_after_attempt(3))
    def _invoke_table(self, input: Chunk, **kwargs) -> List[Output]:
        try:
            input.id = generate_hash_id(input.content)
            table_context_info = self._table_context(input)
            return self._table_extractor(input, table_type)
        except:
            logger.warning(f"_invoke_table failed for chunk:{input}")
            raise RuntimeError(f"table extract failed for chunk:{input}")

        logger.error(f"_invoke_table failed for chunk, return None:{input}")
        return []

    def _table_extractor(self, input_table: Chunk, table_context_info: TableDefaultInfo):
        if (
            table_type.lower() in ["矩阵型表格", "matrixtable"]
            or "matrix" in table_type.lower()
        ):
            return self._extract_metric_table(input_table)
        elif table_type.lower() in ["简单表格", "simpletable"]:
            return self._extract_simple_table(input_table)
        return self._extract_other_table(input_table)

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

    def _get_row_column_desc_by_llm(self, input_table: Chunk, table_df: pd.DataFrame):
        table_info: TableDefaultInfo = input_table.kwargs["table_info"]
        table_desc = table_info.desc
        input_str = table_desc + "\n\n" + table_df.to_markdown(index=False)
        matrix_table_info = self.llm.invoke(
            variables={"input": input_str},
            prompt_op=self.matrix_table_index_prompt,
            with_json_parse=True,
            with_except=True,
        )
        return matrix_table_info

    def _gen_table_row_and_col_desc(self, input_table: Chunk):
        """
        generate table row and column description
        """


    def _extract_metric_table(self, input_table: Chunk):
        html_content = markdown.markdown(
            input_table.content, extensions=["markdown.extensions.tables"]
        )
        table_df = pd.read_html(StringIO(html_content))[0]
        table_cell_desc = self._get_table_cell_desc(
            input_table=input_table, table_df=table_df
        )
        subgraph = self._generate_subgraph(
            input_table=input_table, table_df=table_df, table_cell_desc=table_cell_desc
        )
        return [subgraph]

    def _get_table_cell_desc(self, input_table: Chunk, table_df: pd.DataFrame):
        table_cell_desc = TableCellDesc()
        matrix_table_info = self._get_row_column_desc_by_llm(
            input_table=input_table, table_df=table_df
        )
        row_desc_list = matrix_table_info["rows"]
        column_desc_list = matrix_table_info["columns"]
        table_cell_desc.row_desc_list = row_desc_list
        table_cell_desc.column_desc_list = column_desc_list
        row_num, column_num = table_df.shape
        skip_row = row_num - len(row_desc_list)
        table_cell_desc.df_skip_row = skip_row
        skip_column = column_num - len(column_desc_list)
        table_cell_desc.df_skip_column = skip_column
        for row_index, row in table_df.iterrows():
            if row_index < skip_row:
                continue
            column_index = 0
            for _, value in row.items():
                if column_index < skip_column:
                    column_index += 1
                    continue
                row_desc = row_desc_list[row_index - skip_row]
                column_desc = column_desc_list[column_index - skip_column]
                key = str(row_index - skip_row) + "_" + str(column_index - skip_column)
                desc = row_desc + " of " + column_desc + " is " + str(value)
                table_cell = TableCellValue(
                    value=value, desc=desc, row_name=row_desc, column_name=column_desc
                )
                table_cell_desc.desc_dict[key] = table_cell
                column_index += 1
        return table_cell_desc

    def _generate_subgraph(
        self,
        input_table: Chunk,
        table_df: pd.DataFrame,
        table_cell_desc: TableCellDesc = None,
        with_cell_node: bool = False,
    ):
        nodes = []
        edges = []

        table_id = input_table.id

        table_info: TableDefaultInfo = input_table.kwargs.pop("table_info")

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

        if table_cell_desc is not None:
            # TableRow nodes
            row_desc_list = table_cell_desc.row_desc_list
            skip_row = table_cell_desc.df_skip_row
            for row_index, row in table_df.iterrows():
                if row_index < skip_row:
                    continue
                row_desc = row_desc_list[row_index - skip_row]
                node = Node(
                    _id=f"{table_id}-row-{row_index}",
                    name=f"{table_name}-{row_desc}",
                    label="TableRow",
                    properties={
                        "raw_name": row_desc,
                        "content": row.to_csv(),
                    },
                )
                nodes.append(node)
            # TableColumn nodes
            column_desc_list = table_cell_desc.column_desc_list
            skip_column = table_cell_desc.df_skip_column
            col_index = -1
            for col_name, col_data in table_df.iteritems():
                col_index += 1
                if col_index < skip_column:
                    continue
                column_desc = column_desc_list[col_index - skip_column]
                node = Node(
                    _id=f"{table_id}-column-{col_index}",
                    name=f"{table_name}-{column_desc}",
                    label="TableColumn",
                    properties={
                        "raw_name": column_desc,
                        "content":col_data.to_csv(),
                    },
                )
                nodes.append(node)
            # TableCell nodes
            if with_cell_node:
                for cell_key, table_cell in table_cell_desc.desc_dict.items():
                    table_cell: TableCellValue = table_cell
                    node = Node(
                        _id=f"{table_id}-cell-{cell_key}",
                        name=f"{table_name} shows {table_cell.desc}",
                        label="TableCell",
                        properties={
                            "raw_name": table_cell.desc,
                            "row_name": table_cell.row_name,
                            "col_name": table_cell.column_name,
                            "desc": table_cell.desc,
                            "value": table_cell.value,
                            "scale": table_cell.scale,
                            "unit": table_cell.unit,
                        },
                    )
                    nodes.append(node)

        node_map = {}
        for node in nodes:
            node_map[node.id] = node

        if table_cell_desc is not None:
            # table <-> row
            row_desc_list = table_cell_desc.row_desc_list
            for idx, row_desc in enumerate(row_desc_list):
                row_id = f"{table_id}-row-{idx}"
                edge = Edge(
                    _id=f"table-{table_id}-row-{idx}",
                    from_node=node_map[table_id],
                    to_node=node_map[row_id],
                    label="containRow",
                    properties={},
                )

                edges.append(edge)

                edge = Edge(
                    _id=f"row-{idx}-table-{table_id}",
                    from_node=node_map[row_id],
                    to_node=node_map[table_id],
                    label="partOf",
                    properties={},
                )
                edges.append(edge)

            # table <-> column
            column_desc_list = table_cell_desc.column_desc_list
            for idx, column_desc in enumerate(column_desc_list):
                col_id = f"{table_id}-column-{idx}"
                edge = Edge(
                    _id=f"table-{table_id}-col-{idx}",
                    from_node=node_map[table_id],
                    to_node=node_map[col_id],
                    label="containColumn",
                    properties={},
                )
                edges.append(edge)

                edge = Edge(
                    _id=f"col-{idx}-table-{table_id}",
                    from_node=node_map[col_id],
                    to_node=node_map[table_id],
                    label="partOf",
                    properties={},
                )
                edges.append(edge)

            # table/row/col <-> table cell
            if with_cell_node:
                for cell_key, table_cell in table_cell_desc.desc_dict.items():
                    table_cell: TableCellValue = table_cell
                    cell_id = f"{table_id}-cell-{cell_key}"
                    row_index = cell_key.split("_")
                    column_index = row_index[1]
                    row_index = row_index[0]

                    row_id = f"{table_id}-row-{row_index}"
                    col_id = f"{table_id}-column-{column_index}"
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
                        to_node=node_map[table_id],
                        label="partOfTable",
                        properties={},
                    )
                    edges.append(edge)

        subgraph = SubGraph(nodes=nodes, edges=edges)
        return subgraph

    def _extract_simple_table(self, input_table: Chunk):
        rst = []
        subgraph = self._generate_subgraph(
            input_table=input_table, table_df=None, table_cell_desc=None
        )
        rst.append(subgraph)

        # 调用ner进行实体识别
        table_chunks = self.split_table(input_table, 500)
        for c in table_chunks:
            subgraph_list = self.schema_free_extractor._invoke(input=c)
            rst.extend(subgraph_list)
        return rst

    def _extract_other_table(self, input_table: Chunk):
        return self._extract_simple_table(input_table=input_table)

    def split_table(self, org_chunk: Chunk, chunk_size: int = 2000, sep: str = "\n"):
        """
        Internal method to split a markdown format table into smaller markdown tables.

        Args:
            org_chunk (Chunk): The original chunk containing the table data.
            chunk_size (int): The maximum size of each smaller chunk. Defaults to 2000.
            sep (str): The separator used to join the table rows. Defaults to "\n".

        Returns:
            List[Chunk]: A list of smaller chunks resulting from the split operation.
        """
        output = []
        content = org_chunk.content
        table_start = content.find("|")
        table_end = content.rfind("|") + 1
        if table_start is None or table_end is None or table_start == table_end:
            return None
        prefix = content[0:table_start].strip("\n ")
        table_rows = content[table_start:table_end].split("\n")
        table_header = table_rows[0]
        table_header_segmentation = table_rows[1]
        suffix = content[table_end:].strip("\n ")

        splitted = []
        cur = [prefix, table_header, table_header_segmentation]
        cur_len = len(prefix)
        for idx, row in enumerate(table_rows[2:]):
            if cur_len > chunk_size:
                cur.append(suffix)
                splitted.append(cur)
                cur_len = 0
                cur = [prefix, table_header, table_header_segmentation]
            cur.append(row)
            cur_len += len(row)

        cur.append(content[table_end:])
        if len(cur) > 0:
            splitted.append(cur)

        output = []
        for idx, sentences in enumerate(splitted):
            chunk = Chunk(
                id=f"{org_chunk.id}#{chunk_size}#table#{idx}#LEN",
                name=f"{org_chunk.name}#{idx}",
                content=sep.join(sentences),
                type=org_chunk.type,
                **org_chunk.kwargs,
            )
            output.append(chunk)
        return output
