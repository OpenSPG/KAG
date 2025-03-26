from pyvis.network import Network
import textwrap

from kag.builder.model.sub_graph import SubGraph


def visualize_graph(
    subgraph: SubGraph, output_path: str = "document_graph", format: str = "html"
):
    """
    Visualize the SubGraph using Pyvis and save it as an interactive HTML file.

    Args:
        subgraph: The SubGraph to visualize
        output_path: Path where to save the output file (without extension)
        format: Output format, currently only supports 'html'
    """
    # 创建网络图
    net = Network(
        notebook=True,
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="black",
    )
    net.force_atlas_2based()  # 使用力导向布局

    def wrap_text(text: str, width: int = 30) -> str:
        """将文本按指定宽度换行"""
        if not text:
            return ""
        return "<br>".join(textwrap.wrap(text, width=width))

    # 节点颜色映射
    node_colors = {
        "Title": "#B0E0E6",  # 浅蓝色
        "Chunk": "#E0FFE0",  # 浅绿色
        "Table": "#FFEFD5",  # 浅橙色
    }

    # 边的样式映射
    edge_styles = {
        "has_child": ("#2B60DE", 2),  # 蓝色
        "has_parent": ("#2B60DE", 1),  # 蓝色
        "has_content": ("#228B22", 2),  # 绿色
        "belongs_to": ("#228B22", 1),  # 绿色
        "has_table": ("#FF8C00", 2),  # 橙色
        "describes": ("#9370DB", 2),  # 紫色
        "described_by": ("#9370DB", 1),  # 紫色
        "contains": ("#4169E1", 2),  # 皇家蓝
        "reverse_contains": ("#4169E1", 1),  # 皇家蓝
    }

    # 添加节点
    for node in subgraph.nodes:
        # 准备节点标签
        if node.label == "Title":
            content = node.properties.get("content", "")
            if content:
                content_preview = (
                    content[:100] + "..." if len(content) > 100 else content
                )
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = node.name
            size = 30  # 标题节点大一些
        elif node.label == "Chunk":
            content = node.properties.get("content", "")
            if content:
                content_preview = (
                    content[:100] + "..." if len(content) > 100 else content
                )
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = f"{node.name}<br>(empty content)"
            size = 25
        else:  # Table
            headers = node.properties.get("headers", "")
            if isinstance(headers, list):
                headers = ", ".join(str(h) for h in headers)
            content = node.properties.get("content", "")
            if content:
                content_preview = (
                    content[:100] + "..." if len(content) > 100 else content
                )
                label = f"{node.name}<br><br>{wrap_text(content_preview)}"
            else:
                label = f"{node.name}<br>{wrap_text(headers)}"
            size = 25

        # 添加节点
        net.add_node(
            node.id,
            label=label,
            color=node_colors.get(node.label, "#FFFFFF"),
            size=size,
            font={"size": 12, "face": "Microsoft YaHei"},
            shape="box",
            margin=10,
            mass=2 if node.label == "Title" else 1,
        )  # 标题节点质量大些，更稳定

    # 添加边
    for edge in subgraph.edges:
        style = edge_styles.get(edge.label, ("#000000", 1))
        net.add_edge(
            edge.from_id,
            edge.to_id,
            label=edge.label,
            color=style[0],
            width=style[1],
            arrows={"to": {"enabled": True, "type": "arrow"}},
            font={"size": 10, "face": "Microsoft YaHei"},
        )

    # 设置物理布局参数
    net.set_options(
        """
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
    """
    )

    # 保存为HTML文件
    try:
        net.save_graph(f"{output_path}.html")
    except:
        try:
            net.write_html(f"{output_path}.html")
        except:
            net.show(f"{output_path}.html")
