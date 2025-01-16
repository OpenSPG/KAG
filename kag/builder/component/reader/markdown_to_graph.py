from typing import Dict, List, Tuple
from pyvis.network import Network
import textwrap

from kag.builder.model.sub_graph import SubGraph, Node, Edge
from kag.builder.component.reader.markdown_reader import MarkdownNode
from kag.builder.model.chunk import Chunk

def visualize_graph(subgraph: SubGraph, output_path: str = "document_graph", format: str = "html"):
    """
    Visualize the SubGraph using Pyvis and save it as an interactive HTML file.
    
    Args:
        subgraph: The SubGraph to visualize
        output_path: Path where to save the output file (without extension)
        format: Output format, currently only supports 'html'
    """
    # 创建网络图
    net = Network(notebook=True, height="900px", width="100%", bgcolor="#ffffff", font_color="black")
    net.force_atlas_2based()  # 使用力导向布局
    
    def wrap_text(text: str, width: int = 30) -> str:
        """将文本按指定宽度换行"""
        if not text:
            return ""
        return '<br>'.join(textwrap.wrap(text, width=width))
    
    # 节点颜色映射
    node_colors = {
        "Title": "#B0E0E6",  # 浅蓝色
        "Chunk": "#E0FFE0",  # 浅绿色
        "Table": "#FFEFD5"   # 浅橙色
    }
    
    # 边的样式映射
    edge_styles = {
        'has_child': ('#2B60DE', 2),      # 蓝色
        'has_parent': ('#2B60DE', 1),     # 蓝色
        'has_content': ('#228B22', 2),    # 绿色
        'belongs_to': ('#228B22', 1),     # 绿色
        'has_table': ('#FF8C00', 2),      # 橙色
        'describes': ('#9370DB', 2),      # 紫色
        'described_by': ('#9370DB', 1),   # 紫色
        'contains': ('#4169E1', 2),       # 皇家蓝
        'reverse_contains': ('#4169E1', 1) # 皇家蓝
    }
    
    # 添加节点
    for node in subgraph.nodes:
        # 准备节点标签
        if node.label == "Title":
            content = node.properties.get('content', '')
            if content:
                content_preview = content[:100] + '...' if len(content) > 100 else content
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = node.name
            size = 30  # 标题节点大一些
        elif node.label == "Chunk":
            content = node.properties.get('content', '')
            if content:
                content_preview = content[:100] + '...' if len(content) > 100 else content
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = f"{node.name}<br>(empty content)"
            size = 25
        else:  # Table
            headers = node.properties.get('headers', '')
            if isinstance(headers, list):
                headers = ', '.join(str(h) for h in headers)
            content = node.properties.get('content', '')
            if content:
                content_preview = content[:100] + '...' if len(content) > 100 else content
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = f"{node.name}<br>{wrap_text(headers)}"
            size = 25
        
        # 添加节点
        net.add_node(node.id, 
                    label=label, 
                    color=node_colors.get(node.label, "#FFFFFF"),
                    size=size,
                    font={'size': 12, 'face': 'Microsoft YaHei'},
                    shape='box',
                    margin=10,
                    mass=2 if node.label == "Title" else 1)  # 标题节点质量大些，更稳定
    
    # 添加边
    for edge in subgraph.edges:
        style = edge_styles.get(edge.label, ('#000000', 1))
        net.add_edge(edge.from_id, 
                    edge.to_id,
                    label=edge.label,
                    color=style[0],
                    width=style[1],
                    arrows={'to': {'enabled': True, 'type': 'arrow'}},
                    font={'size': 10, 'face': 'Microsoft YaHei'})
    
    # 设置物理布局参数
    net.set_options("""
    var options = {
        "physics": {
            "enabled": false
        },
        "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true,
            "dragNodes": true,
            "dragView": true,
            "zoomView": true
        },
        "layout": {
            "hierarchical": {
                "enabled": true,
                "direction": "UD",
                "sortMethod": "directed",
                "nodeSpacing": 200,
                "treeSpacing": 300,
                "levelSeparation": 250,
                "blockShifting": true,
                "edgeMinimization": true,
                "parentCentralization": false,
                "shakeTowards": "roots"
            }
        },
        "nodes": {
            "font": {
                "size": 12,
                "face": "Microsoft YaHei"
            },
            "shape": "box",
            "margin": 10,
            "widthConstraint": {
                "minimum": 100,
                "maximum": 300
            }
        },
        "edges": {
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "vertical",
                "roundness": 0.5
            }
        }
    }
    """)
    
    # 保存为HTML文件
    try:
        net.save_graph(f"{output_path}.html")
    except:
        try:
            net.write_html(f"{output_path}.html")
        except:
            net.show(f"{output_path}.html")

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