import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Tuple

import numpy as np

from kag.jiuyuansolver.pg_impl import PostgresDB

logger = logging.getLogger(__name__)

class LogsImporter:
    def __init__(self, db_config: Dict[str, Any], model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化日志导入器
        
        Args:
            db_config: 数据库配置
            model_name: 文本向量化模型名称，仅在原始向量不存在时使用
        """
        self.db = PostgresDB(db_config)
        
    async def connect(self):
        """连接数据库"""
        await self.db.connect()

    def sync_connect(self):
        """连接数据库"""
        self.db.sync_connect()
        
    async def close(self):
        """关闭数据库连接"""
        await self.db.close()

    def sync_close(self):
        """关闭数据库连接"""
        self.db.sync_close()
        
    def _load_logs_raw(self, file_path: str) -> Dict[str, Any]:
        """
        加载logs_raw数据
        
        Args:
            file_path: 日志文件路径
            
        Returns:
            解析后的日志数据
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            logger.info(f"正在读取文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ValueError(f"文件为空: {file_path}")
                logger.debug(f"文件内容前100个字符: {content[:100]}")
                try:
                    data = json.loads(content)
                    return data
                except json.JSONDecodeError as je:
                    logger.error(f"JSON解析错误: {str(je)}")
                    logger.error(f"错误位置附近的内容: {content[max(0, je.pos-50):je.pos+50]}")
                    raise
        except Exception as e:
            logger.error(f"加载logs_raw文件失败: {str(e)}")
            raise
            

    def _process_subgraph(self, subgraph: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        处理子图数据，使用已有的向量数据或生成新的向量表示
        
        Args:
            subgraph: 子图数据
            
        Returns:
            处理后的节点列表和边列表
        """
        nodes = []
        edges = []
        
        # 处理sub_graph结构
        if "sub_graph" in subgraph:
            subgraph = subgraph["sub_graph"]
            
        # 处理节点
        nodes_data = subgraph.get("resultNodes", [])
        if not isinstance(nodes_data, list):
            nodes_data = [nodes_data]
            
        for node in nodes_data:
            try:
                # 获取已有的向量数据或生成新的向量
                name_vector = None
                desc_vector = None
                content_vector=None
                properties = node.get("properties", {})
                
                # 从properties中获取已有的向量
                if isinstance(properties, dict):
                    name_vector = properties.get("_name_vector")
                    desc_vector = properties.get("_desc_vector")
                    content_vector = properties.get("_content_vector")
                    
                    # 移除向量数据，因为它们会单独存储
                    properties = {k: v for k, v in properties.items() if not k.startswith('_')}
                
                # 确保properties和向量数据都是JSON字符串
                properties_str = json.dumps(properties, ensure_ascii=False)
                name_vector_str = json.dumps(name_vector) if name_vector is not None else None
                desc_vector_str = json.dumps(desc_vector) if desc_vector is not None else None
                content_vector_str = json.dumps(content_vector) if content_vector is not None else None
                
                nodes.append({
                    "node_id": str(node.get("id")),  # 确保id是字符串
                    "name":node.get("name"),
                    "label": node.get("label"),
                    "properties": properties_str,
                    "name_vector": name_vector_str,
                    "desc_vector": desc_vector_str,
                    "content_vector":content_vector_str
                })
            except Exception as e:
                logger.error(f"处理节点时出错: {str(e)}")
                logger.error(f"问题节点数据: {node}")
                continue
                    
        # 处理边
        edges_data = subgraph.get("resultEdges", [])
        if not isinstance(edges_data, list):
            edges_data = [edges_data]
            
        for edge in edges_data:
            try:
                # 获取已有的向量数据或生成新的向量
                name_vector = None
                desc_vector = None
                content_vector=None
                properties = edge.get("properties", {})
                
                # 从properties中获取已有的向量
                if isinstance(properties, dict):
                    name_vector = properties.get("_name_vector")
                    desc_vector = properties.get("_desc_vector")
                    content_vector = properties.get("_content_vector")
                    # 移除向量数据，因为它们会单独存储
                    properties = {k: v for k, v in properties.items() if not k.startswith('_')}
                
                # 确保properties和向量数据都是JSON字符串
                properties_str = json.dumps(properties, ensure_ascii=False)
                name_vector_str = json.dumps(name_vector) if name_vector is not None else None
                desc_vector_str = json.dumps(desc_vector) if desc_vector is not None else None
                content_vector_str = json.dumps(content_vector) if content_vector is not None else None
                
                edges.append({
                    "source_id": str(edge.get("from")),  # 确保id是字符串
                    "target_id": str(edge.get("to")),    # 确保id是字符串
                    "edge_type": edge.get("label"),
                    "properties": properties_str,
                    "name_vector": name_vector_str,
                    "desc_vector": desc_vector_str,
                    "content_vector":content_vector_str
                })
            except Exception as e:
                logger.error(f"处理边时出错: {str(e)}")
                logger.error(f"问题边数据: {edge}")
                continue
                
        return nodes, edges
        


    def _process_subgraph_data(self, nodes, edges) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        res_nodes = []
        res_edges = []
        for node in nodes:
            try:
                # 获取已有的向量数据或生成新的向量
                name_vector = None
                desc_vector = None
                content_vector=None
                properties = node['properties']
                
                # 从properties中获取已有的向量
                if isinstance(properties, dict):
                    name_vector = properties.get("_name_vector")
                    desc_vector = properties.get("_desc_vector")
                    content_vector = properties.get("_content_vector")
                    # 移除向量数据，因为它们会单独存储
                    properties = {k: v for k, v in properties.items() if not k.startswith('_')}

                # 确保properties和向量数据都是JSON字符串
                properties_str = json.dumps(properties, ensure_ascii=False)
                name_vector_str = json.dumps(name_vector) if name_vector is not None else None
                desc_vector_str = json.dumps(desc_vector) if desc_vector is not None else None
                content_vector_str = json.dumps(content_vector) if content_vector is not None else None
                
                res_nodes.append({
                    "node_id": str(node['id']),  # 确保id是字符串
                    "name":node['name'],
                    "label": node['label'],
                    "properties": properties_str,
                    "name_vector": name_vector_str,
                    "desc_vector": desc_vector_str,
                    "content_vector":content_vector_str
                })
            except Exception as e:
                logger.error(f"处理节点时出错: {str(e)}")
                logger.error(f"问题节点数据: {node}")
                continue

        for edge in edges:
            try:
                # 获取已有的向量数据或生成新的向量
                name_vector = None
                desc_vector = None
                content_vector=None
                properties = edge['properties']
                
                # 从properties中获取已有的向量
                if isinstance(properties, dict):
                    name_vector = properties.get("_name_vector")
                    desc_vector = properties.get("_desc_vector")
                    content_vector = properties.get("_content_vector")
                    # 移除向量数据，因为它们会单独存储
                    properties = {k: v for k, v in properties.items() if not k.startswith('_')}
                
                # 确保properties和向量数据都是JSON字符串
                properties_str = json.dumps(properties, ensure_ascii=False)
                name_vector_str = json.dumps(name_vector) if name_vector is not None else None
                desc_vector_str = json.dumps(desc_vector) if desc_vector is not None else None
                content_vector_str = json.dumps(content_vector) if content_vector is not None else None
                
                res_edges.append({
                    "source_id": edge['from'],  # 确保id是字符串
                    "target_id": edge['to'],    # 确保id是字符串
                    "edge_type": edge['label'],
                    "properties": properties_str,
                    "name_vector": name_vector_str,
                    "desc_vector": desc_vector_str,
                    "content_vector":content_vector_str
                })
            except Exception as e:
                logger.error(f"处理边时出错: {str(e)}")
                logger.error(f"问题边数据: {edge}")
                continue

        return res_nodes, res_edges


    async def import_logs(self, logs_path: str) -> None:
        """
        导入日志数据
        
        Args:
            logs_path: 日志文件或目录的路径
        """
        try:
            # 初始化数据表
            await self.db.init_graph_tables()
            
            # 检查路径是文件还是目录
            if os.path.isfile(logs_path):
                # 如果是文件，直接处理
                logger.info(f"Processing file: {logs_path}")
                data = self._load_logs_raw(logs_path)
                
                # 如果数据是列表，处理每个子图
                if isinstance(data, list):
                    for subgraph in data:
                        nodes, edges = self._process_subgraph(subgraph)
                        await self.db.import_subgraph({"nodes": nodes, "edges": edges})
                # 如果数据是单个子图
                else:
                    print("单个子图")
                    nodes, edges = self._process_subgraph(data)
                    await self.db.import_subgraph({"nodes": nodes, "edges": edges})
                    
                logger.info(f"Successfully processed file: {logs_path}")
            else:
                raise FileNotFoundError(f"Path not found: {logs_path}")
                
        except Exception as e:
            logger.error(f"Failed to import logs: {str(e)}")
            raise

    def sync_import_logs(self, logs_path: str) -> None:
        """
        导入日志数据（同步版本）
        
        Args:
            logs_path: 日志文件或目录的路径
        """
        try:
            # 初始化数据表
            self.db.sync_init_graph_tables()
            
            # # 检查路径是文件还是目录
            if os.path.isfile(logs_path):
                # 如果是文件，直接处理
                logger.info(f"Processing file: {logs_path}")
                data = self._load_logs_raw(logs_path)
                
                # 如果数据是列表，处理每个子图
                if isinstance(data, list):
                    for subgraph in data:
                        nodes, edges = self._process_subgraph(subgraph)
                        self.db.sync_import_subgraph({"nodes": nodes, "edges": edges})
                # 如果数据是单个子图
                else:
                    print("单个子图")
                    nodes, edges = self._process_subgraph(data)
                    self.db.sync_import_subgraph({"nodes": nodes, "edges": edges})
                    
                logger.info(f"Successfully processed file: {logs_path}")
            else:
                raise FileNotFoundError(f"Path not found: {logs_path}")
                
        except Exception as e:
            logger.error(f"Failed to import logs: {str(e)}")
            raise

async def main():
    # 数据库配置
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "wr",
        "password": "your_password",
        "database": "test"
    }
    
    # 创建导入器实例
    importer = LogsImporter(db_config)
    
    try:
        # 连接数据库
        await importer.connect()
        
        # 导入数据
        await importer.import_logs("/root/softwares/kag_project/KAG-master/kag/jiuyuansolver/logs_raw")
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
    finally:
        # 关闭连接
        await importer.close()

def sync_main():
    # 数据库配置
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "wr",
        "password": "your_password",
        "database": "test"
    }
    
    # 创建导入器实例
    importer = LogsImporter(db_config)
    
    try:
        # 连接数据库
        importer.sync_connect()
        
        # 导入数据
        importer.sync_import_logs("/root/softwares/kag_project/KAG-master/kag/jiuyuansolver/logs_raw")
        
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
    finally:
        # 关闭连接
        importer.sync_close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # asyncio.run(main()) 
    sync_main()