from typing import Dict, List, Tuple
import graphviz

from kag.builder.model.sub_graph import SubGraph, Node, Edge
from kag.builder.component.reader.markdown_reader import MarkdownNode
from kag.builder.model.chunk import Chunk

def visualize_graph(subgraph: SubGraph, output_path: str = "document_graph", format: str = "svg"):
    """
    Visualize the SubGraph using Graphviz and save it as a vector or raster image file.
    
    Args:
        subgraph: The SubGraph to visualize
        output_path: Path where to save the output image (without extension)
        format: Output format, either 'svg' for vector graphics or 'png' for raster graphics
    """
    dot = graphviz.Digraph(comment='Document Structure', format=format)
    # 设置图形属性以提高清晰度
    dot.attr(rankdir='TB',  # Top to bottom layout
            size='100,100',  # 增加图的尺寸
            ratio='expand',  # 自动扩展以适应尺寸
            margin='0.5',
            nodesep='0.8',  # 增加节点间距
            ranksep='2.0')  # 增加层级间距
    
    # SVG特定的属性
    if format == 'svg':
        dot.attr(bgcolor='transparent')  # 透明背景
    else:
        dot.attr(dpi='600')  # 仅在PNG格式时设置DPI
    
    # 创建子图，每个层级一个子图
    clusters = {}
    
    # 设置全局节点样式
    dot.attr('node', 
            shape='box', 
            style='rounded,filled',
            fontsize='16',  # 增加字体大小
            height='0.8',
            width='2.5',
            margin='0.3')
    
    # 添加节点，按标签类型使用不同的颜色
    for node in subgraph.nodes:
        if node.label == "Title":
            # 蓝色标题节点
            level = node.properties.get('level', 'N/A')
            if level not in clusters:
                clusters[level] = graphviz.Digraph(name=f'cluster_{level}')
                clusters[level].attr(label=f'Level {level}',
                                   style='rounded',
                                   color='blue',
                                   fontsize='18',
                                   margin='30')
            
            clusters[level].node(node.id, 
                               f"{node.name}", 
                               color='#2B60DE',  # 深蓝色边框
                               fillcolor='#B0E0E6',  # 浅蓝色填充
                               penwidth='2.5')  # 加粗边框
        
        elif node.label == "Chunk":
            # 绿色内容节点
            content = node.properties.get('content', '')
            if content:
                content = content[:40] + '...' if len(content) > 40 else content
            dot.node(node.id, 
                    f"Content:\\n{content}", 
                    color='#228B22',  # 深绿色边框
                    fillcolor='#E0FFE0',  # 浅绿色填充
                    penwidth='2.5')
        
        elif node.label == "Table":
            # 橙色表格节点
            headers = node.properties.get('headers', '')
            headers = headers[:40] + '...' if len(headers) > 40 else headers
            dot.node(node.id, 
                    f"{node.name}\\n{headers}", 
                    color='#FF8C00',  # 深橙色边框
                    fillcolor='#FFEFD5',  # 浅橙色填充
                    penwidth='2.5')
    
    # 将子图添加到主图
    for cluster in clusters.values():
        dot.subgraph(cluster)
    
    # 添加边，使用不同的颜色和样式
    edge_styles = {
        'has_child': ('#2B60DE', 'solid', '2.0'),     # 蓝色实线
        'has_parent': ('#2B60DE', 'dashed', '1.5'),   # 蓝色虚线
        'has_content': ('#228B22', 'solid', '2.0'),   # 绿色实线
        'belongs_to': ('#228B22', 'dashed', '1.5'),   # 绿色虚线
        'has_table': ('#FF8C00', 'solid', '2.0'),     # 橙色实线
        'describes': ('#9370DB', 'solid', '2.0'),     # 紫色实线
        'described_by': ('#9370DB', 'dashed', '1.5'), # 紫色虚线
        'contains': ('#4169E1', 'solid', '2.0'),      # 皇家蓝实线
        'reverse_contains': ('#4169E1', 'dashed', '1.5')  # 皇家蓝虚线
    }
    
    # 设置边的属性
    dot.attr('edge', 
            fontsize='14',  # 边标签字体大小
            fontcolor='#444444',  # 边标签颜色
            arrowsize='1.0')  # 箭头大小
    
    for edge in subgraph.edges:
        style = edge_styles.get(edge.label, ('black', 'solid', '1.0'))
        dot.edge(edge.from_id, 
                edge.to_id, 
                edge.label,
                color=style[0],  # 边的颜色
                style=style[1],  # 边的样式
                penwidth=style[2],  # 边的宽度
                dir='both' if style[1] == 'solid' else 'forward')
    
    # 保存图形，使用高质量设置
    dot.render(output_path, format=format, cleanup=True)

def get_graph_statistics(subgraph: SubGraph) -> dict:
    """
    Collect comprehensive statistics about the graph structure.
    
    Args:
        subgraph: The SubGraph to analyze
        
    Returns:
        dict: A dictionary containing detailed statistics about nodes, edges and connectivity
    """
    stats = {
        "nodes": {
            "total": len(subgraph.nodes),
            "by_type": {},
            "examples": {}
        },
        "edges": {
            "total": len(subgraph.edges),
            "by_type": {},
            "examples": {}
        },
        "connectivity": {
            "average": 0,
            "max": 0,
            "min": 0,
            "most_connected": []
        }
    }
    
    # Node statistics
    node_types = {}
    for node in subgraph.nodes:
        node_types[node.label] = node_types.get(node.label, 0) + 1
        
        # Collect examples
        if node.label not in stats["nodes"]["examples"]:
            stats["nodes"]["examples"][node.label] = []
        if len(stats["nodes"]["examples"][node.label]) < 3:
            example = {
                "name": node.name,
                "id": node.id
            }
            if node.label == "Title":
                example["level"] = node.properties.get('level', 'N/A')
            elif node.label == "Table":
                example["headers"] = node.properties.get('headers', '')[:100]
            elif node.label == "Chunk":
                example["content"] = node.properties.get('content', '')[:100]
            stats["nodes"]["examples"][node.label].append(example)
    
    stats["nodes"]["by_type"] = node_types
    
    # Edge statistics
    edge_types = {}
    for edge in subgraph.edges:
        edge_types[edge.label] = edge_types.get(edge.label, 0) + 1
        
        # Collect examples
        if edge.label not in stats["edges"]["examples"]:
            stats["edges"]["examples"][edge.label] = []
        if len(stats["edges"]["examples"][edge.label]) < 3:
            from_node = next((n for n in subgraph.nodes if n.id == edge.from_id), None)
            to_node = next((n for n in subgraph.nodes if n.id == edge.to_id), None)
            if from_node and to_node:
                stats["edges"]["examples"][edge.label].append({
                    "from": {"id": from_node.id, "name": from_node.name},
                    "to": {"id": to_node.id, "name": to_node.name}
                })
    
    stats["edges"]["by_type"] = edge_types
    
    # Connectivity statistics
    node_connections = {}
    for edge in subgraph.edges:
        node_connections[edge.from_id] = node_connections.get(edge.from_id, 0) + 1
        node_connections[edge.to_id] = node_connections.get(edge.to_id, 0) + 1
    
    if node_connections:
        stats["connectivity"]["average"] = sum(node_connections.values()) / len(node_connections)
        stats["connectivity"]["max"] = max(node_connections.values())
        stats["connectivity"]["min"] = min(node_connections.values())
        
        # Find most connected nodes
        most_connected = sorted([(k, v) for k, v in node_connections.items()], 
                              key=lambda x: x[1], reverse=True)[:3]
        for node_id, connections in most_connected:
            node = next((n for n in subgraph.nodes if n.id == node_id), None)
            if node:
                stats["connectivity"]["most_connected"].append({
                    "id": node.id,
                    "name": node.name,
                    "label": node.label,
                    "connections": connections
                })
    
    return stats

def convert_to_subgraph(root: MarkdownNode, chunks: List[Chunk], node_chunk_map: Dict[MarkdownNode, Chunk]) -> Tuple[SubGraph, dict]:
    """
    Convert a MarkdownNode tree and its corresponding chunks into a SubGraph structure.
    
    Args:
        root: The root MarkdownNode of the document tree
        chunks: List of Chunk objects representing the document content
        node_chunk_map: Mapping between MarkdownNode objects and their corresponding Chunk objects
        
    Returns:
        Tuple[SubGraph, dict]: A tuple containing:
            - SubGraph: A graph representation of the document structure with:
                - Directory hierarchy (parent-child title relationships)
                - Title to chunk relationships
                - Title to table relationships
            - dict: Comprehensive statistics about the graph structure
    """
    nodes = []
    edges = []
    
    # Keep track of created nodes to avoid duplicates
    node_map = {}
    chunk_nodes = {}  # Track chunk nodes by their IDs
    
    def add_bidirectional_edge(from_node: Node, to_node: Node, label: str, properties: Dict = None):
        """Helper function to add bidirectional edges"""
        if properties is None:
            properties = {}
            
        # Forward edge
        edges.append(Edge(
            _id="",
            from_node=from_node,
            to_node=to_node,
            label=label,
            properties=properties.copy()
        ))
        
        # Backward edge
        reverse_label = {
            "has_child": "has_parent",
            "has_content": "belongs_to_title",
            "has_table": "belongs_to_title"
        }.get(label, f"reverse_{label}")
        
        edges.append(Edge(
            _id="",
            from_node=to_node,
            to_node=from_node,
            label=reverse_label,
            properties=properties.copy()
        ))
    
    def process_node(node: MarkdownNode, parent_node: Node = None):
        # Create node ID based on title or root
        node_id = f"node_{hash(node.title if node.title != 'root' else 'root')}"
        
        # Create title node if not exists
        if node_id not in node_map:
            title_node = Node(
                _id=node_id,
                name=node.title,
                label="Title",
                properties={"level": str(node.level)}
            )
            nodes.append(title_node)
            node_map[node_id] = title_node
        else:
            title_node = node_map[node_id]
        
        # Create edge from parent title if exists
        if parent_node:
            add_bidirectional_edge(
                parent_node,
                title_node,
                "has_child",
                {"level": str(node.level)}
            )
        
        # Get corresponding chunk if exists
        chunk = node_chunk_map.get(node)
        if chunk:
            # Create chunk node
            chunk_node = Node(
                _id=chunk.id,
                name=chunk.name,
                label="Chunk",
                properties={
                    "content": chunk.content,
                    "parent_content": chunk.parent_content,
                    "type": str(chunk.type)
                }
            )
            nodes.append(chunk_node)
            chunk_nodes[chunk.id] = chunk_node
            
            # Create bidirectional edges between title and chunk
            add_bidirectional_edge(title_node, chunk_node, "has_content")
        
        # Process tables if any
        for i, table in enumerate(node.tables):
            table_id = f"{node_id}_table_{i}"
            table_node = Node(
                _id=table_id,
                name=f"Table {i+1}",
                label="Table",
                properties={
                    "headers": ",".join(table["headers"]),
                    "context_before": table.get("context", {}).get("before_text", ""),
                    "context_after": table.get("context", {}).get("after_text", "")
                }
            )
            nodes.append(table_node)
            
            # Create bidirectional edges between title and table
            add_bidirectional_edge(title_node, table_node, "has_table")
        
        # Process children recursively
        for child in node.children:
            process_node(child, title_node)
    
    # Start processing from root
    process_node(root)
    
    subgraph = SubGraph(nodes=nodes, edges=edges)
    stats = get_graph_statistics(subgraph)
    
    return subgraph, stats 