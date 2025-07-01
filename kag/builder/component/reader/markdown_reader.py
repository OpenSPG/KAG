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

# Standard library imports
import io
import logging
import os
import re
from typing import Dict, List, Tuple

# Third-party imports
from kag.interface.builder.base import BuilderComponentData
import markdown
import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

# Local imports
from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.builder.model.sub_graph import Edge, Node, SubGraph
from kag.builder.prompt.analyze_table_prompt import AnalyzeTablePrompt
from kag.common.utils import generate_hash_id
from kag.interface import ReaderABC
from knext.common.base.runnable import Input, Output

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class MarkdownNode:
    """Represents a node in the markdown document tree structure."""

    def __init__(self, title: str, level: int, content: str = ""):
        self.title = title
        self.level = level
        self.content = content
        self.children: List[MarkdownNode] = []
        self.tables: List[Dict] = []  # Store table data


# ============================================================================
# SubGraph Conversion Functions
# ============================================================================


def convert_to_subgraph(
    root: MarkdownNode, chunks: List[Chunk], node_chunk_map: Dict[MarkdownNode, Chunk]
) -> Tuple[SubGraph, dict]:
    """
    Convert a MarkdownNode tree and its corresponding chunks into a SubGraph structure.

    Args:
        root: The root MarkdownNode of the document tree
        chunks: List of Chunk objects representing the document content
        node_chunk_map: Mapping between MarkdownNode objects and their corresponding Chunk objects

    Returns:
        Tuple[SubGraph, dict]: A tuple containing:
            - SubGraph: A graph representation of the document structure
            - dict: Comprehensive statistics about the graph structure
    """
    nodes = []
    edges = []
    node_map = {}  # Track created nodes to avoid duplicates
    chunk_nodes = {}  # Track chunk nodes by their IDs

    def _add_bidirectional_edge(
        from_node: Node, to_node: Node, label: str, properties: Dict = None
    ) -> None:
        """Add bidirectional edges between two nodes."""
        if properties is None:
            properties = {}

        # Forward edge
        edges.append(
            Edge(
                _id="",
                from_node=from_node,
                to_node=to_node,
                label=label,
                properties=properties.copy(),
            )
        )

        # Backward edge
        reverse_label_map = {
            "hasChild": "hasParent",
            "hasContent": "belongsToTitle",
            "hasTable": "belongsToTitle",
        }
        reverse_label = reverse_label_map.get(label, f"reverse_{label}")

        edges.append(
            Edge(
                _id="",
                from_node=to_node,
                to_node=from_node,
                label=reverse_label,
                properties=properties.copy(),
            )
        )

    def _process_node(node: MarkdownNode, parent_node: Node = None) -> None:
        """Process a markdown node and create corresponding graph nodes."""
        # Create unique node ID
        node_title = node.title if node.title != "root" else "root"
        node_id = f"node_{hash(node_title)}"

        # Create or get title node
        if node_id not in node_map:
            title_node = Node(
                _id=node_id,
                name=node.title,
                label="Title",
                properties={"level": str(node.level)},
            )
            nodes.append(title_node)
            node_map[node_id] = title_node
        else:
            title_node = node_map[node_id]

        # Link to parent if exists
        if parent_node:
            _add_bidirectional_edge(
                parent_node, title_node, "hasChild", {"level": str(node.level)}
            )

        # Process corresponding chunk
        chunk = node_chunk_map.get(node)
        if chunk:
            chunk_node = Node(
                _id=chunk.id,
                name=chunk.name,
                label="Chunk",
                properties={
                    "content": chunk.content,
                    "parentContent": chunk.parent_content,
                    "type": str(chunk.type),
                },
            )
            nodes.append(chunk_node)
            chunk_nodes[chunk.id] = chunk_node
            _add_bidirectional_edge(title_node, chunk_node, "hasContent")

        # Process tables
        for i, table in enumerate(node.tables):
            table_id = f"{node_id}_table_{i}"
            table_node = Node(
                _id=table_id,
                name=f"Table {i+1}",
                label="Table",
                properties={
                    "headers": ",".join(table["headers"]),
                    "context_before": table.get("context", {}).get("before_text", ""),
                    "context_after": table.get("context", {}).get("after_text", ""),
                },
            )
            nodes.append(table_node)
            _add_bidirectional_edge(title_node, table_node, "hasTable")

        # Process children recursively
        for child in node.children:
            _process_node(child, title_node)

    # Start processing from root
    _process_node(root)

    subgraph = SubGraph(nodes=nodes, edges=edges)
    stats = get_graph_statistics(subgraph)

    return subgraph, stats


def get_graph_statistics(subgraph: SubGraph) -> dict:
    """
    Collect comprehensive statistics about the graph structure.

    Args:
        subgraph: The SubGraph to analyze

    Returns:
        dict: A dictionary containing detailed statistics about nodes, edges and connectivity
    """
    stats = {
        "nodes": {"total": len(subgraph.nodes), "by_type": {}, "examples": {}},
        "edges": {"total": len(subgraph.edges), "by_type": {}, "examples": {}},
        "connectivity": {"average": 0, "max": 0, "min": 0, "most_connected": []},
    }

    # Collect node statistics
    node_types = {}
    for node in subgraph.nodes:
        node_types[node.label] = node_types.get(node.label, 0) + 1

        # Collect examples (max 3 per type)
        if node.label not in stats["nodes"]["examples"]:
            stats["nodes"]["examples"][node.label] = []

        if len(stats["nodes"]["examples"][node.label]) < 3:
            example = {"name": node.name, "id": node.id}

            if node.label == "Title":
                example["level"] = node.properties.get("level", "N/A")
            elif node.label == "Table":
                example["headers"] = node.properties.get("headers", "")[:100]
            elif node.label == "Chunk":
                example["content"] = node.properties.get("content", "")[:100]

            stats["nodes"]["examples"][node.label].append(example)

    stats["nodes"]["by_type"] = node_types

    # Collect edge statistics
    edge_types = {}
    for edge in subgraph.edges:
        edge_types[edge.label] = edge_types.get(edge.label, 0) + 1

        # Collect examples (max 3 per type)
        if edge.label not in stats["edges"]["examples"]:
            stats["edges"]["examples"][edge.label] = []

        if len(stats["edges"]["examples"][edge.label]) < 3:
            from_node = next((n for n in subgraph.nodes if n.id == edge.from_id), None)
            to_node = next((n for n in subgraph.nodes if n.id == edge.to_id), None)

            if from_node and to_node:
                stats["edges"]["examples"][edge.label].append(
                    {
                        "from": {"id": from_node.id, "name": from_node.name},
                        "to": {"id": to_node.id, "name": to_node.name},
                    }
                )

    stats["edges"]["by_type"] = edge_types

    # Calculate connectivity statistics
    node_connections = {}
    for edge in subgraph.edges:
        node_connections[edge.from_id] = node_connections.get(edge.from_id, 0) + 1
        node_connections[edge.to_id] = node_connections.get(edge.to_id, 0) + 1

    if node_connections:
        connection_values = list(node_connections.values())
        stats["connectivity"]["average"] = sum(connection_values) / len(
            connection_values
        )
        stats["connectivity"]["max"] = max(connection_values)
        stats["connectivity"]["min"] = min(connection_values)

        # Find most connected nodes (top 3)
        most_connected = sorted(
            node_connections.items(), key=lambda x: x[1], reverse=True
        )[:3]

        for node_id, connections in most_connected:
            node = next((n for n in subgraph.nodes if n.id == node_id), None)
            if node:
                stats["connectivity"]["most_connected"].append(
                    {
                        "id": node.id,
                        "name": node.name,
                        "label": node.label,
                        "connections": connections,
                    }
                )

    return stats


# ============================================================================
# Main Reader Classes
# ============================================================================


@ReaderABC.register("md")
@ReaderABC.register("md_reader")
class MarkDownReader(ReaderABC):
    """
    A class for reading MarkDown files and converting them into structured chunks.

    This reader parses markdown content, extracts hierarchical structure,
    and creates chunks based on heading levels and content organization.

    Args:
        cut_depth (int): The depth of cutting, determining the level of detail in parsing. Default is 3.
        reserve_meta (bool): Whether to preserve metadata in chunks. Default is False.
        length_splitter (LengthSplitter): Optional splitter for handling long content.
    """

    # Class constants
    ALL_LEVELS = [f"h{x}" for x in range(1, 7)]
    TABLE_CHUCK_FLAG = "<<<table_chuck>>>"

    def __init__(
        self,
        cut_depth: int = 3,
        reserve_meta: bool = False,
        length_splitter: LengthSplitter = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.cut_depth = int(cut_depth)
        self.analyze_table_prompt = AnalyzeTablePrompt(language="zh")
        self.analyze_img_prompt = AnalyzeTablePrompt(language="zh")
        self.length_splitter = length_splitter
        self.reserve_meta = reserve_meta

    @property
    def input_types(self):
        return str

    @property
    def output_types(self):
        return Tuple[
            List[Chunk], Dict[MarkdownNode, Chunk], MarkdownNode, Tuple[SubGraph, dict]
        ]

    def solve_content(
        self, id: str, title: str, content: str, **kwargs
    ) -> Tuple[List[Output], SubGraph]:
        """
        Process markdown content and convert it to structured chunks and subgraph.

        Args:
            id: Unique identifier for the content
            title: Title of the content
            content: Raw markdown content

        Returns:
            Tuple containing processed chunks and subgraph representation
        """
        # Preprocess content
        content = self._preprocess_markdown_content(content)

        # Convert to HTML and parse
        html = markdown.markdown(
            content, extensions=["tables", "nl2br", "sane_lists", "fenced_code"]
        )
        soup = BeautifulSoup(html, "html.parser")

        # Build document tree
        root = self._build_document_tree(soup)

        # Convert to outputs
        outputs, node_chunk_map = self._convert_to_outputs(root, id)

        # Apply length splitting if configured
        if self.length_splitter:
            outputs, node_chunk_map = self._apply_length_splitting(
                outputs, node_chunk_map
            )

        # Create subgraph representation
        flat_node_chunk_map = self._flatten_node_chunk_map(node_chunk_map)
        subgraph, _ = convert_to_subgraph(root, outputs, flat_node_chunk_map)

        return outputs, subgraph

    def _preprocess_markdown_content(self, content: str) -> str:
        """Preprocess markdown content to normalize formatting."""
        # Remove leading spaces from heading lines
        content = re.sub(r"^\s+(#+\s)", r"\1", content, flags=re.MULTILINE)
        # Ensure blank line before headings
        content = re.sub(r"(?<=[^\n])\n(#+\s)", r"\n\n\1", content)

        # Add a default title if content doesn't start with #
        lines = content.strip().split("\n")
        if lines and not lines[0].strip().startswith("#"):
            content = f"# {lines[0].strip()}\n\n" + content

        return content

    def _build_document_tree(self, soup: BeautifulSoup) -> MarkdownNode:
        """Build a hierarchical document tree from parsed HTML."""
        root = MarkdownNode("root", 0)
        stack = [root]
        current_content = []

        # Helper functions
        def _is_in_code_block(element):
            """Check if an element is inside a code block."""
            parent = element.parent
            while parent:
                if parent.name in ["pre", "code"]:
                    return True
                parent = parent.parent
            return False

        def _process_text_with_links(element):
            """Process text containing links, preserving original markdown format."""
            result = []
            current_text = ""

            for child in element.children:
                if isinstance(child, Tag):
                    if child.name == "a":
                        if current_text:
                            result.append(current_text.strip())
                            current_text = ""

                        # Rebuild markdown format link
                        link_text = child.get_text().strip()
                        href = child.get("href", "")
                        title = child.get("title", "")

                        if title:
                            result.append(f'[{link_text}]({href} "{title}")')
                        else:
                            result.append(f"[{link_text}]({href})")
                    else:
                        current_text += child.get_text()
                else:
                    current_text += str(child)

            if current_text:
                result.append(current_text.strip())

            return " ".join(result)

        def _process_table(element):
            """Process table element and extract structured data."""
            table_html = str(element)
            try:
                df = pd.read_html(io.StringIO(table_html), header=0)[0]
                df = df.astype(str)

                # Clean up data
                for col in df.columns:
                    df[col] = df[col].map(
                        lambda x: str(x).strip('"\\"') if isinstance(x, str) else x
                    )

                # Clean headers
                df.columns = [
                    "" if "Unnamed" in str(col) else str(col).strip('"\\"')
                    for col in df.columns
                ]
                headers = df.columns.tolist()

                # Extract context
                context = self._extract_table_context(element, _process_text_with_links)

                return {"headers": headers, "data": df, "context": context}
            except Exception:
                return None

        # Process all elements
        all_elements = soup.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "p",
                "table",
                "ul",
                "ol",
                "li",
                "pre",
                "code",
            ]
        )

        for element in all_elements:
            if element.name.startswith("h") and not _is_in_code_block(element):
                # Handle headers
                if current_content and stack[-1].title != "root":
                    stack[-1].content = "\n".join(current_content)
                current_content = []

                level = int(element.name[1])
                title_text = _process_text_with_links(element)
                new_node = MarkdownNode(title_text, level)

                # Adjust stack based on heading level
                while stack and stack[-1].level >= level:
                    stack.pop()

                if stack:
                    stack[-1].children.append(new_node)
                stack.append(new_node)

            elif element.name == "code":
                # Preserve code blocks
                text = element.get_text()
                if text:
                    current_content.append(text)

            elif element.name in ["ul", "ol"]:
                continue

            elif element.name == "li":
                # Process list items
                text = _process_text_with_links(element)
                if text:
                    if element.find_parent("ol"):
                        index = len(element.find_previous_siblings("li")) + 1
                        current_content.append(f"{index}. {text}")
                    else:
                        current_content.append(f"* {text}")

            elif element.name == "table":
                # Process tables
                table_data = _process_table(element)
                if table_data and stack[-1].title != "root":
                    stack[-1].tables.append(table_data)

            elif element.name == "p":
                # Process paragraphs
                text = _process_text_with_links(element)
                if (
                    text
                    and not text.startswith("* ")
                    and not re.match(r"^\d+\. ", text)
                ):
                    current_content.append(text)

        # Process final content
        if current_content and stack[-1].title != "root":
            stack[-1].content = "\n".join(current_content)

        return root

    def _extract_table_context(self, table_element, text_processor):
        """Extract context text before and after a table."""
        context = {"before_text": "", "after_text": ""}

        # Get text before table
        prev_texts = []
        prev_element = table_element.find_previous_sibling()
        while prev_element:
            if prev_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break
            if prev_element.name == "p":
                prev_texts.insert(0, text_processor(prev_element))
            prev_element = prev_element.find_previous_sibling()
        context["before_text"] = "\n".join(prev_texts) if prev_texts else ""

        # Get text after table
        next_texts = []
        next_element = table_element.find_next_sibling()
        while next_element:
            if next_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break
            if next_element.name == "p":
                next_texts.append(text_processor(next_element))
            next_element = next_element.find_next_sibling()
        context["after_text"] = "\n".join(next_texts) if next_texts else ""

        return context

    def _convert_to_outputs(
        self,
        node: MarkdownNode,
        id: str,
        parent_id: str = None,
        parent_titles: List[str] = None,
        parent_contents: List[str] = None,
    ) -> Tuple[List[Output], Dict[MarkdownNode, Output]]:
        """Convert markdown node tree to output chunks."""

        def _convert_table_to_markdown(headers, data):
            """Convert table data to markdown format."""
            if not headers or data.empty:
                return ""
            data = data.fillna("").astype(str)
            return "\n" + data.to_markdown(index=False) + "\n"

        def _collect_tables(n: MarkdownNode, recursive: bool = False):
            """Collect tables from node and optionally its children."""
            tables = []
            table_md = []

            if n.tables:
                for table in n.tables:
                    tables.append(table)
                    table_md.append(
                        _convert_table_to_markdown(table["headers"], table["data"])
                    )

            if recursive:
                for child in n.children:
                    child_tables, child_table_md = _collect_tables(child, True)
                    tables.extend(child_tables)
                    table_md.extend(child_table_md)

            return tables, table_md

        def _collect_children_content(n: MarkdownNode):
            """Collect content from node and its children recursively."""
            content = []
            if n.content:
                content.append(n.content)
            for child in n.children:
                content.extend(_collect_children_content(child))
            return content

        outputs = []
        node_chunk_map = {}

        if parent_titles is None:
            parent_titles = []
        if parent_contents is None:
            parent_contents = []

        current_titles = parent_titles + ([node.title] if node.title != "root" else [])

        # Process based on node level relative to cut depth
        if node.level >= self.cut_depth:
            outputs, node_chunk_map = self._process_target_level_node(
                node,
                id,
                parent_id,
                current_titles,
                parent_contents,
                _convert_table_to_markdown,
                _collect_tables,
            )
        elif node.level < self.cut_depth:
            outputs, node_chunk_map = self._process_intermediate_level_node(
                node,
                id,
                parent_id,
                current_titles,
                parent_contents,
                _convert_table_to_markdown,
                _collect_tables,
                _collect_children_content,
            )

        return outputs, node_chunk_map

    def _process_target_level_node(
        self,
        node,
        id,
        parent_id,
        current_titles,
        parent_contents,
        convert_table_func,
        collect_tables_func,
    ):
        """Process nodes at target cut depth level."""
        outputs = []
        node_chunk_map = {}

        full_title = " / ".join(current_titles)
        parent_content = (
            "\n".join(filter(None, parent_contents)) if parent_contents else None
        )

        # Collect current and child content
        current_content = [node.content] if node.content else []
        for child in node.children:
            child_content = self._collect_children_content_recursive(child)
            current_content.extend(child_content)

        # Create main chunk
        main_chunk = Chunk(
            id=generate_hash_id(full_title),
            parent_id=parent_id,
            name=full_title,
            content="\n".join(filter(None, current_content)),
            parent_content=parent_content if self.reserve_meta else None,
        )
        outputs.append(main_chunk)
        node_chunk_map[node] = main_chunk

        # Create table chunks
        outputs.extend(
            self._create_table_chunks(
                node,
                full_title,
                main_chunk.id,
                id,
                convert_table_func,
                collect_tables_func,
            )
        )

        return outputs, node_chunk_map

    def _process_intermediate_level_node(
        self,
        node,
        id,
        parent_id,
        current_titles,
        parent_contents,
        convert_table_func,
        collect_tables_func,
        collect_children_content_func,
    ):
        """Process nodes below target cut depth level."""
        outputs = []
        node_chunk_map = {}

        current_contents = parent_contents + ([node.content] if node.content else [])
        has_target_level = False

        # Create chunk for current node if it has content
        if node.content and node.title != "root":
            full_title = " / ".join(current_titles)
            parent_content = (
                "\n".join(filter(None, parent_contents)) if parent_contents else None
            )

            current_chunk = Chunk(
                id=generate_hash_id(full_title),
                parent_id=parent_id,
                name=full_title,
                content=node.content,
                parent_content=parent_content if self.reserve_meta else "",
            )
            outputs.append(current_chunk)
            node_chunk_map[node] = current_chunk

        # Process children
        for child in node.children:
            child_outputs, child_map = self._convert_to_outputs(
                child, id, parent_id, current_titles, current_contents
            )
            if child_outputs:
                has_target_level = True
                outputs.extend(child_outputs)
                node_chunk_map.update(child_map)

        # If no target level found, create comprehensive chunk
        if not has_target_level and node.title != "root":
            outputs, node_chunk_map = self._create_comprehensive_chunk(
                node,
                id,
                parent_id,
                current_titles,
                parent_contents,
                convert_table_func,
                collect_children_content_func,
            )

        return outputs, node_chunk_map

    def _collect_children_content_recursive(self, node: MarkdownNode):
        """Recursively collect content from a node and its children."""
        content = []
        if node.content:
            content.append(node.content)
        for child in node.children:
            content.extend(self._collect_children_content_recursive(child))
        return content

    def _create_table_chunks(
        self,
        node,
        full_title,
        parent_chunk_id,
        file_id,
        convert_table_func,
        collect_tables_func,
    ):
        """Create separate chunks for tables."""
        table_chunks = []
        all_tables = []

        # Process node's own tables
        if node.tables:
            for i, table in enumerate(node.tables):
                table_content = convert_table_func(table["headers"], table["data"])
                table_chunk = Chunk(
                    id=generate_hash_id(f"{full_title} / Table {i+1}"),
                    parent_id=parent_chunk_id,
                    name=f"{full_title} / Table {i+1}",
                    content=table_content,
                    type=ChunkTypeEnum.Table,
                    before_text=table.get("context", {}).get("before_text", ""),
                    after_text=table.get("context", {}).get("after_text", ""),
                    file_name=os.path.basename(file_id),
                )
                table_chunks.append(table_chunk)
                all_tables.append(table)

        # Process children's tables
        for child in node.children:
            child_tables, _ = collect_tables_func(child, recursive=True)
            for i, table in enumerate(child_tables, start=len(all_tables)):
                table_content = convert_table_func(table["headers"], table["data"])
                table_chunk = Chunk(
                    id=generate_hash_id(f"{full_title} / Table {i+1}"),
                    parent_id=parent_chunk_id,
                    name=f"{full_title} / Table {i+1}",
                    content=table_content,
                    type=ChunkTypeEnum.Table,
                    before_text=table.get("context", {}).get("before_text", ""),
                    after_text=table.get("context", {}).get("after_text", ""),
                    file_name=os.path.basename(file_id),
                )
                table_chunks.append(table_chunk)

        return table_chunks

    def _create_comprehensive_chunk(
        self,
        node,
        id,
        parent_id,
        current_titles,
        parent_contents,
        convert_table_func,
        collect_children_content_func,
    ):
        """Create a comprehensive chunk when no target level is found."""
        outputs = []
        node_chunk_map = {}

        full_title = " / ".join(current_titles)
        parent_content = (
            "\n".join(filter(None, parent_contents)) if parent_contents else None
        )

        # Collect all content
        current_content = [node.content] if node.content else []
        for child in node.children:
            child_content = collect_children_content_func(child)
            current_content.extend(child_content)

        main_chunk = Chunk(
            id=generate_hash_id(full_title),
            parent_id=parent_id,
            name=full_title,
            content="\n".join(filter(None, current_content)),
            parent_content=parent_content if self.reserve_meta else "",
        )
        outputs.append(main_chunk)
        node_chunk_map[node] = main_chunk

        # Add table chunks
        if node.tables:
            for i, table in enumerate(node.tables):
                table_content = convert_table_func(table["headers"], table["data"])
                table_chunk = Chunk(
                    id=generate_hash_id(f"{full_title} / Table {i+1}"),
                    parent_id=main_chunk.id,
                    name=f"{full_title} / Table {i+1}",
                    content=table_content,
                    type=ChunkTypeEnum.Table,
                    before_text=table.get("context", {}).get("before_text", ""),
                    after_text=table.get("context", {}).get("after_text", ""),
                    file_name=os.path.basename(id),
                )
                outputs.append(table_chunk)

        return outputs, node_chunk_map

    def _apply_length_splitting(self, outputs, node_chunk_map):
        """Apply length splitting to long chunks."""
        new_outputs = []
        new_node_chunk_map = {}

        for output in outputs:
            split_chunks = self.length_splitter.slide_window_chunk(output)
            for chunk in split_chunks:
                chunk.parent_id = output.parent_id
            new_outputs.extend(split_chunks)

            # Update node mapping
            related_nodes = [
                node for node, chunk in node_chunk_map.items() if chunk.id == output.id
            ]
            for node in related_nodes:
                if node not in new_node_chunk_map:
                    new_node_chunk_map[node] = []
                new_node_chunk_map[node].extend(split_chunks)

        return new_outputs, new_node_chunk_map

    def _flatten_node_chunk_map(self, node_chunk_map):
        """Flatten node chunk mapping for subgraph conversion."""
        if self.length_splitter:
            return {
                node: chunks[0] for node, chunks in node_chunk_map.items() if chunks
            }
        return node_chunk_map

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Process a Markdown file and return its content as structured chunks.

        Args:
            input: The path to the Markdown file or Chunk object
            **kwargs: Additional keyword arguments

        Returns:
            List[Output]: A list of processed content chunks
        """
        # Parse input
        content, basename, id = self._parse_input(input)

        # Process content
        chunks, subgraph = self.solve_content(str(id), basename, content)

        # Log statistics
        self._log_chunk_statistics(chunks)

        return chunks

    def _parse_input(self, input: Input) -> Tuple[str, str, str]:
        """Parse different input types and extract content, basename, and id."""
        if isinstance(input, str):
            file_path = input
            if not file_path.endswith(".md"):
                raise ValueError(f"Please provide a markdown file, got {file_path}")
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"The file {file_path} does not exist.")

            with open(file_path, "r", encoding="utf-8") as reader:
                content = reader.read()
            basename, _ = os.path.splitext(os.path.basename(file_path))
            return content, basename, input

        elif isinstance(input, Chunk):
            content = input.content.replace("\\n", "\n")
            return content, input.name, input.id

        elif isinstance(input, list):
            if len(input) == 0:
                raise ValueError("Input list is empty")

            first_item = input[0]
            if isinstance(first_item, str):
                return first_item, first_item, first_item
            elif isinstance(first_item, Chunk):
                content = first_item.content
                return content, first_item.name, first_item.id
            elif isinstance(first_item, BuilderComponentData):
                content = first_item.data.content
                return content, first_item.data.name, first_item.data.id
            else:
                raise TypeError(
                    f"Expected file path or Chunk, got {type(first_item).__name__}"
                )
        else:
            raise TypeError(f"Expected file path or Chunk, got {type(input).__name__}")

    def _log_chunk_statistics(self, chunks: List[Chunk]) -> None:
        """Log statistics about chunk lengths."""
        length_categories = {
            "small": [],  # <= 500
            "medium": [],  # 501-1000
            "large": [],  # 1001-5000
            "extra_large": [],  # > 5000
        }

        table_count = 0

        for chunk in chunks:
            # Count table chunks
            if chunk.type == ChunkTypeEnum.Table:
                table_count += 1

            if chunk.content is not None:
                content_length = len(chunk.content)
                if content_length <= 500:
                    length_categories["small"].append(chunk)
                elif content_length <= 1000:
                    length_categories["medium"].append(chunk)
                elif content_length <= 5000:
                    length_categories["large"].append(chunk)
                else:
                    length_categories["extra_large"].append(chunk)

        # Log statistics
        logger.info("Chunk statistics:")
        logger.info(f"  Total chunks: {len(chunks)}")
        logger.info(f"  Table chunks: {table_count}")
        logger.info(f"  Small chunks (≤500): {len(length_categories['small'])}")
        logger.info(f"  Medium chunks (501-1000): {len(length_categories['medium'])}")
        logger.info(f"  Large chunks (1001-5000): {len(length_categories['large'])}")
        logger.info(
            f"  Extra large chunks (>5000): {len(length_categories['extra_large'])}"
        )


# ============================================================================
# Specialized Readers
# ============================================================================


@ReaderABC.register("yuque")
@ReaderABC.register("yuque_reader")
class YuequeReader(MarkDownReader):
    """
    A specialized reader for parsing Yueque documents into Chunk objects.

    This class inherits from MarkDownReader and provides functionality to process
    Yueque documents by fetching content via API and converting it to structured chunks.
    """

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Process a Yueque document and convert it into chunks.

        Args:
            input: String containing Yueque token and URL in format "token@url"
            **kwargs: Additional keyword arguments

        Returns:
            List[Output]: A list of Chunk objects representing the parsed content

        Raises:
            HTTPError: If the request to the Yueque URL fails
        """
        # Parse token and URL
        token, url = input.split("@", 1)

        # Fetch content from Yueque API
        headers = {"X-Auth-Token": token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Extract document data
        data = response.json()["data"]
        doc_id = data.get("id", "")
        title = data.get("title", "")
        content = data.get("body", "")

        # Process content using parent class logic
        chunks, subgraph = self.solve_content(str(doc_id), title, content)
        return chunks


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    reader = ReaderABC.from_config(
        {
            "type": "md",
            "cut_depth": 3,
        }
    )

    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        dir_path, "../../../../tests/unit/builder/data", "需求内容test.md"
    )
    file_path = "/Users/zhangxinhong.zxh/Downloads/overmemery.md"
    chunks = reader.invoke(file_path, write_ckpt=False)
    print(chunks)
