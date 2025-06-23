import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Union

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

import asyncpg
from asyncpg import Connection, Pool
from asyncpg.transaction import Transaction


logger = logging.getLogger(__name__)

class PostgresDB:
    """PostgreSQL数据库操作类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PostgreSQL连接
        
        Args:
            config: 数据库配置信息
                - host: 数据库主机
                - port: 端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - min_size: 连接池最小连接数
                - max_size: 连接池最大连接数
        """
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.user = config.get("user")
        self.password = config.get("password")
        self.database = config.get("database")
        self.min_size = config.get("min_size", 1)
        self.max_size = config.get("max_size", 10)
        self._pool: Optional[Pool] = None
        self._transaction: Optional[Transaction] = None
        self.conn = None
        
    async def connect(self) -> None:
        """创建数据库连接池"""
        try:
            if not self._pool:
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    min_size=self.min_size,
                    max_size=self.max_size
                )
                logger.info(f"Successfully connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    def sync_connect(self) -> None:
        """创建数据库连接池（同步版本）"""
        try:
            if not self.conn:
                self.conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
                logger.info(f"Successfully connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    async def close(self) -> None:
        """关闭数据库连接池"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    def sync_close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("PostgreSQL connection closed")

    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """
        执行SQL语句
        
        Args:
            query: SQL语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            执行结果
        """
        if not self._pool:
            await self.connect()
            
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *args, timeout=timeout)
                return result
        except Exception as e:
            logger.error(f"Failed to execute query: {query}, error: {str(e)}")
            raise

    def sync_execute(self, query: str, *args, timeout: float = None) -> str:
        """
        执行SQL语句
        
        Args:
            query: SQL语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            执行结果
        """
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor() as cur:
                if timeout:
                    cur.execute(f"SET statement_timeout = {int(timeout * 1000)}")
                cur.execute(query, args)
                self.conn.commit()
                return cur.statusmessage
        except Exception as e:
            logger.error(f"Failed to execute query: {query}, error: {str(e)}")
            raise

    async def fetch(self, query: str, *args, timeout: float = None) -> List[Dict[str, Any]]:
        """
        执行查询并返回所有结果
        
        Args:
            query: SQL查询语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            查询结果列表
        """
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *args, timeout=timeout)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch query: {query}, error: {str(e)}")
            raise


    def sync_fetch(self, query: str, *args, timeout: float = None) -> List[Dict[str, Any]]:
        """
        执行查询并返回所有结果
        
        Args:
            query: SQL查询语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            查询结果列表
        """
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if timeout:
                    cur.execute(f"SET statement_timeout = {int(timeout * 1000)}")
                cur.execute(query, args)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch query: {query}, error: {str(e)}")
            raise

    async def fetchrow(self, query: str, *args, timeout: float = None) -> Optional[Dict[str, Any]]:
        """
        执行查询并返回单行结果
        
        Args:
            query: SQL查询语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            单行查询结果
        """
        if not self._pool:
            await self.connect()
    

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, *args, timeout=timeout)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to fetchrow query: {query}, error: {str(e)}")
            raise

    def sync_fetchrow(self, query: str, *args, timeout: float = None) -> Optional[Dict[str, Any]]:
        """
        执行查询并返回单行结果
        
        Args:
            query: SQL查询语句
            args: SQL参数
            timeout: 超时时间(秒)
            
        Returns:
            单行查询结果
        """
        if not self.conn:
            self.connect()
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if timeout:
                    cur.execute(f"SET statement_timeout = {int(timeout * 1000)}")
                cur.execute(query, args)
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to fetchrow query: {query}, error: {str(e)}")
            raise

    async def create_table(self, table_name: str, columns: Dict[str, str], if_not_exists: bool = True, extra_constraints: List[str] = None) -> None:
        """
        创建数据表
        
        Args:
            table_name: 表名
            columns: 列定义字典，key为列名，value为列类型
            if_not_exists: 是否在表不存在时创建
            extra_constraints: 额外的约束条件列表（如外键约束）
        """
        columns_def = ", ".join(f"{name} {type_}" for name, type_ in columns.items())
        if extra_constraints:
            columns_def += ", " + ", ".join(extra_constraints)
            
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause} {table_name} ({columns_def})"
        
        try:
            await self.execute(query)
            logger.info(f"Table {table_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            raise

    def sync_create_table(self, table_name: str, columns: Dict[str, str], if_not_exists: bool = True, extra_constraints: List[str] = None) -> None:
        """
        创建数据表
        
        Args:
            table_name: 表名
            columns: 列定义字典，key为列名，value为列类型
            if_not_exists: 是否在表不存在时创建
            extra_constraints: 额外的约束条件列表（如外键约束）
        """
        columns_def = ", ".join(f"{name} {type_}" for name, type_ in columns.items())
        if extra_constraints:
            columns_def += ", " + ", ".join(extra_constraints)
            
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        query = f"CREATE TABLE {exists_clause} {table_name} ({columns_def})"
        
        try:
            self.sync_execute(query)
            logger.info(f"Table {table_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            raise

    async def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        删除数据表
        
        Args:
            table_name: 表名
            if_exists: 是否在表存在时才删除
        """
        exists_clause = "IF EXISTS" if if_exists else ""
        query = f"DROP TABLE {exists_clause} {table_name} CASCADE"
        
        try:
            await self.execute(query)
            logger.info(f"Table {table_name} dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {str(e)}")
            raise

    def sync_drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        删除数据表
        
        Args:
            table_name: 表名
            if_exists: 是否在表存在时才删除
        """
        exists_clause = "IF EXISTS" if if_exists else ""
        query = f"DROP TABLE {exists_clause} {table_name} CASCADE"
        
        try:
            self.sync_execute(query)
            logger.info(f"Table {table_name} dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {str(e)}")
            raise

    async def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            表是否存在
        """
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = $1
        )
        """
        try:
            result = await self.fetchrow(query, table_name)
            return result["exists"] if result else False
        except Exception as e:
            logger.error(f"Failed to check table existence: {str(e)}")
            raise

    def sync_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            表是否存在
        """
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        )
        """
        try:
            result = self.fetchrow(query, table_name)
            return result["exists"] if result else False
        except Exception as e:
            logger.error(f"Failed to check table existence: {str(e)}")
            raise

    async def begin(self) -> None:
        """开始事务"""
        if not self._pool:
            await self.connect()
        
        if not self._transaction:
            conn = await self._pool.acquire()
            self._transaction = conn.transaction()
            await self._transaction.start()
            logger.debug("Transaction started")

    async def commit(self) -> None:
        """提交事务"""
        if self._transaction:
            await self._transaction.commit()
            if self._transaction.connection:
                await self._pool.release(self._transaction.connection)
            self._transaction = None
            logger.debug("Transaction committed")

    async def rollback(self) -> None:
        """回滚事务"""
        if self._transaction:
            await self._transaction.rollback()
            if self._transaction.connection:
                await self._pool.release(self._transaction.connection)
            self._transaction = None
            logger.debug("Transaction rolled back")

    async def create_index(self, table_name: str, columns: Union[str, List[str]], 
                          index_name: str = None, unique: bool = False, 
                          if_not_exists: bool = True) -> None:
        """
        创建索引
        
        Args:
            table_name: 表名
            columns: 索引列名或列名列表
            index_name: 索引名称
            unique: 是否为唯一索引
            if_not_exists: 是否在索引不存在时创建
        """
        if isinstance(columns, str):
            columns = [columns]
            
        index_name = index_name or f"{table_name}_{'_'.join(columns)}_idx"
        unique_clause = "UNIQUE" if unique else ""
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        columns_str = ", ".join(columns)
        
        query = f"CREATE {unique_clause} INDEX {exists_clause} {index_name} ON {table_name} ({columns_str})"
        
        try:
            await self.execute(query)
            logger.info(f"Index {index_name} created successfully on table {table_name}")
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise

    def sync_create_index(self, table_name: str, columns: Union[str, List[str]], 
                    index_name: str = None, unique: bool = False, 
                    if_not_exists: bool = True) -> None:
        """
        创建索引
        
        Args:
            table_name: 表名
            columns: 索引列名或列名列表
            index_name: 索引名称
            unique: 是否为唯一索引
            if_not_exists: 是否在索引不存在时创建
        """
        if isinstance(columns, str):
            columns = [columns]
            
        index_name = index_name or f"{table_name}_{'_'.join(columns)}_idx"
        unique_clause = "UNIQUE" if unique else ""
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        columns_str = ", ".join(columns)
        
        query = f"CREATE {unique_clause} INDEX {exists_clause} {index_name} ON {table_name} ({columns_str})"
        
        try:
            self.sync_execute(query)
            logger.info(f"Index {index_name} created successfully on table {table_name}")
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise

    async def create_table_with_constraints(self, table_name: str, sql: str) -> None:
        """
        使用完整SQL创建表
        
        Args:
            table_name: 表名
            sql: 完整的建表SQL语句
        """
        try:
            await self.execute(sql)
            logger.info(f"Table {table_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            raise

    def sync_create_table_with_constraints(self, table_name: str, sql: str) -> None:
        """
        使用完整SQL创建表
        
        Args:
            table_name: 表名
            sql: 完整的建表SQL语句
        """
        try:
            if not self.conn:
                self.connect()
                
            with self.conn.cursor() as cur:
                cur.execute(sql)
                self.conn.commit()
            logger.info(f"Table {table_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            raise

    async def init_graph_tables(self) -> None:
        """
        初始化图数据相关的表（节点表和边表）
        """
        await self.drop_table("graph_nodes")
        # 创建节点表
        nodes_sql = """
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id SERIAL PRIMARY KEY,
            node_id VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255),
            label VARCHAR(255),
            properties JSONB,
            name_vector vector(1024),
            desc_vector vector(1024),
            content_vector vector(1024),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self.create_table_with_constraints("graph_nodes", nodes_sql)
        
        await self.drop_table("graph_edges")
        # 创建边表
        edges_sql = """
        CREATE TABLE IF NOT EXISTS graph_edges (
            id SERIAL PRIMARY KEY,
            source_id VARCHAR(255) NOT NULL,
            target_id VARCHAR(255) NOT NULL,
            edge_type VARCHAR(255),
            properties JSONB,
            name_vector vector(1024),
            desc_vector vector(1024),
            content_vector vector(1024),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES graph_nodes(node_id),
            FOREIGN KEY (target_id) REFERENCES graph_nodes(node_id)
        )
        """
        await self.create_table_with_constraints("graph_edges", edges_sql)
        
        # 创建索引
        await self.execute("CREATE INDEX IF NOT EXISTS idx_source_target ON graph_edges(source_id, target_id)")

    def sync_init_graph_tables(self) -> None:
        """
        初始化图数据相关的表（节点表和边表）（同步版本）
        """
        # 同步删除并创建节点表
        self.sync_drop_table("graph_nodes")
        
        nodes_sql = """
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id SERIAL PRIMARY KEY,
            node_id VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255),
            label VARCHAR(255),
            properties JSONB,
            name_vector vector(1024),
            desc_vector vector(1024),
            content_vector vector(1024),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.sync_create_table_with_constraints("graph_nodes", nodes_sql)
        
        # 同步删除并创建边表
        self.sync_drop_table("graph_edges")
        
        edges_sql = """
        CREATE TABLE IF NOT EXISTS graph_edges (
            id SERIAL PRIMARY KEY,
            source_id VARCHAR(255) NOT NULL,
            target_id VARCHAR(255) NOT NULL,
            edge_type VARCHAR(255),
            properties JSONB,
            name_vector vector(1024),
            desc_vector vector(1024),
            content_vector vector(1024),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES graph_nodes(node_id),
            FOREIGN KEY (target_id) REFERENCES graph_nodes(node_id)
        )
        """
        self.sync_create_table_with_constraints("graph_edges", edges_sql)
        
        # 创建索引
        self.sync_execute("CREATE INDEX IF NOT EXISTS idx_source_target ON graph_edges(source_id, target_id)")


    async def batch_insert_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """
        批量插入节点数据
        
        Args:
            nodes: 节点数据列表，每个节点包含：
                  - node_id: 节点ID
                  - label: 节点标签
                  - properties: 节点属性
                  - vector: 向量数据（可选）
        """
        if not nodes:
            return
            
        query = """
        INSERT INTO graph_nodes (node_id, name, label, properties, name_vector, desc_vector, content_vector)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (node_id) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            label = EXCLUDED.label,
            properties = EXCLUDED.properties,
            name_vector = EXCLUDED.name_vector,
            desc_vector = EXCLUDED.desc_vector,
            content_vector = EXCLUDED.content_vector,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.executemany(
                        query,
                        [(
                            node["node_id"],
                            node.get("name"),
                            node.get("label"),
                            node.get("properties", {}),
                            node.get("name_vector"),
                            node.get("desc_vector"),
                            node.get("content_vector")
                        ) for node in nodes]
                    )
            logger.info(f"Successfully inserted {len(nodes)} nodes")
        except Exception as e:
            logger.error(f"Failed to batch insert nodes: {str(e)}")
            raise

    def sync_batch_insert_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """
        批量插入节点数据（同步版本）
        
        Args:
            nodes: 节点数据列表，每个节点包含：
                - node_id: 节点ID
                - name: 节点名称
                - label: 节点标签
                - properties: 节点属性
                - name_vector: 名称向量（可选）
                - desc_vector: 描述向量（可选）
                - content_vector
        """
        if not nodes:
            return
        
        # 同步版本的SQL查询（使用%s占位符）
        query = """
        INSERT INTO graph_nodes (node_id, name, label, properties, name_vector, desc_vector, content_vector)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (node_id) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            label = EXCLUDED.label,
            properties = EXCLUDED.properties,
            name_vector = EXCLUDED.name_vector,
            desc_vector = EXCLUDED.desc_vector,
            content_vector = EXCLUDED.content_vector,
            updated_at = CURRENT_TIMESTAMP
        """
        try:
            if not self.conn:
                self.connect()
                
            with self.conn.cursor() as cur:
                params = [
                    (
                        node["node_id"],
                        node.get("name"),
                        node.get("label"),
                        node.get("properties", {}),
                        node.get("name_vector"),
                        node.get("desc_vector"),
                        node.get("content_vector")
                    )
                    for node in nodes
                ]
                cur.executemany(query, params)
                self.conn.commit()
            logger.info(f"Successfully inserted {len(nodes)} nodes")
        except Exception as e:
            logger.error(f"Failed to batch insert nodes: {str(e)}")
            raise

    async def batch_insert_edges(self, edges: List[Dict[str, Any]]) -> None:
        """
        批量插入边数据
        
        Args:
            edges: 边数据列表，每个边包含：
                  - source_id: 源节点ID
                  - target_id: 目标节点ID
                  - edge_type: 边类型
                  - properties: 边属性
                  - vector: 向量数据（可选）
        """
        if not edges:
            return
            
        query = """
        INSERT INTO graph_edges (source_id, target_id, edge_type, properties, name_vector, desc_vector, content_vector)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.executemany(
                        query,
                        [(
                            edge["source_id"],
                            edge["target_id"],
                            edge.get("edge_type"),
                            edge.get("properties", {}),
                            edge.get("name_vector"),
                            edge.get("desc_vector"),
                            edge.get("content_vector")
                        ) for edge in edges]
                    )
            logger.info(f"Successfully inserted {len(edges)} edges")
        except Exception as e:
            logger.error(f"Failed to batch insert edges: {str(e)}")
            raise

    def sync_batch_insert_edges(self, edges: List[Dict[str, Any]]) -> None:
        """
        批量插入边数据（同步版本）
        
        Args:
            edges: 边数据列表，每个边包含：
                - source_id: 源节点ID
                - target_id: 目标节点ID
                - edge_type: 边类型
                - properties: 边属性
                - name_vector: 名称向量（可选）
                - desc_vector: 描述向量（可选）
                - content_vector
        """
        if not edges:
            return
        
        # 同步版本的SQL查询（使用%s占位符）
        query = """
        INSERT INTO graph_edges (source_id, target_id, edge_type, properties, name_vector, desc_vector, content_vector)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            if not self.conn:
                self.connect()
                
            with self.conn.cursor() as cur:
                params = [
                    (
                        edge["source_id"],
                        edge["target_id"],
                        edge.get("edge_type"),
                        edge.get("properties", {}),
                        edge.get("name_vector"),
                        edge.get("desc_vector"),
                        edge.get("content_vector")
                    )
                    for edge in edges
                ]
                cur.executemany(query, params)
                self.conn.commit()
            logger.info(f"Successfully inserted {len(edges)} edges")
        except Exception as e:
            logger.error(f"Failed to batch insert edges: {str(e)}")
            raise


    async def import_subgraph(self, subgraph: Dict[str, Any]) -> None:
        """
        导入子图数据
        
        Args:
            subgraph: 子图数据，包含：
                     - nodes: 节点列表
                     - edges: 边列表
        """
        try:
            
            # 导入节点
            if "nodes" in subgraph:
                await self.batch_insert_nodes(subgraph["nodes"])
            
            # 导入边
            if "edges" in subgraph:
                await self.batch_insert_edges(subgraph["edges"])
                
            logger.info("Successfully imported subgraph data")
        except Exception as e:
            logger.error(f"Failed to import subgraph: {str(e)}")
            raise


    def sync_import_subgraph(self, subgraph: Dict[str, Any]) -> None:
        """
        导入子图数据（同步版本）
        
        Args:
            subgraph: 子图数据，包含：
                    - nodes: 节点列表
                    - edges: 边列表
        """
        try:
            # 导入节点
            if "nodes" in subgraph:
                self.sync_batch_insert_nodes(subgraph["nodes"])
            
            # 导入边
            if "edges" in subgraph:
                self.sync_batch_insert_edges(subgraph["edges"])
                
            logger.info("Successfully imported subgraph data")
        except Exception as e:
            logger.error(f"Failed to import subgraph: {str(e)}")
            raise

    async def query_neighbors(self, node_id: str, direction: str = "both", 
                            edge_type: str = None, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        查询节点的邻居
        
        Args:
            node_id: 节点ID
            direction: 方向，可选 "in"/"out"/"both"
            edge_type: 边类型过滤
            limit: 返回结果数量限制
            
        Returns:
            包含节点和边信息的字典
        """
        try:
            nodes_query = """
            WITH relevant_edges AS (
                SELECT DISTINCT 
                    CASE 
                        WHEN source_id = $1 THEN target_id 
                        ELSE source_id 
                    END as neighbor_id
                FROM graph_edges
                WHERE ($2 = 'both' AND (source_id = $1 OR target_id = $1))
                   OR ($2 = 'out' AND source_id = $1)
                   OR ($2 = 'in' AND target_id = $1)
                   AND ($3::VARCHAR IS NULL OR edge_type = $3)
                LIMIT $4
            )
            SELECT n.* 
            FROM graph_nodes n
            JOIN relevant_edges r ON n.node_id = r.neighbor_id
            """
            
            edges_query = """
            SELECT e.* 
            FROM graph_edges e
            WHERE (($2 = 'both' AND (source_id = $1 OR target_id = $1))
                   OR ($2 = 'out' AND source_id = $1)
                   OR ($2 = 'in' AND target_id = $1))
                   AND ($3::VARCHAR IS NULL OR edge_type = $3)
            LIMIT $4
            """
            
            # 并行执行查询
            async with self._pool.acquire() as conn:
                nodes, edges = await asyncio.gather(
                    conn.fetch(nodes_query, node_id, direction, edge_type, limit),
                    conn.fetch(edges_query, node_id, direction, edge_type, limit)
                )
            
            return {
                "nodes": [dict(node) for node in nodes],
                "edges": [dict(edge) for edge in edges]
            }
        except Exception as e:
            logger.error(f"Failed to query neighbors: {str(e)}")
            raise

    async def find_most_similar_vector(self, vector: List[float], property_key: str = "name", table: str = "graph_nodes", node_type: Optional[str] = None, threshold =0.1, topk: int = 1) -> List[Dict[str, Any]]:
        """
        使用余弦相似度查找最相近的向量
        
        Args:
            vector: 输入向量
            vector_field: 要比较的向量字段名称（name_vector 或 desc_vector）
            table: 要搜索的表名
            topk: 返回的最相近的前k
            
        Returns:
            最相似的记录列表，按相似度降序排序
        """
        try:

            embedding_string = ",".join(map(str, vector))

            vector_field = "name_vector" if property_key == "name" else ("desc_vector" if property_key == "desc" else "content_vector")

            query = f"""SELECT * FROM (SELECT id, name, node_id, label, properties, {vector_field}, 1 - ({vector_field} <=> '[{embedding_string}]'::vector) as score FROM {table} {f"WHERE label = $3" if node_type else ""}) WHERE score>$2 ORDER BY score DESC LIMIT $1 """
            
            # 准备参数
            params = []
            params.extend([topk, threshold])
            if node_type:
                params.append(node_type)

            # 执行查询
            results = await self.fetch(query, *params)
            # print(results)

            return results
            
        except Exception as e:
            logger.error(f"查找相似向量时出错: {str(e)}")
            raise


    def sync_find_most_similar_vector(self, vector: List[float], property_key: str = "name", table: str = "graph_nodes", node_type: Optional[str] = None, threshold =0.1, topk: int = 1) -> List[Dict[str, Any]]:
        """
        使用余弦相似度查找最相近的向量
        
        Args:
            vector: 输入向量
            vector_field: 要比较的向量字段名称（name_vector 或 desc_vector）
            table: 要搜索的表名
            topk: 返回的最相近的前k
            
        Returns:
            最相似的记录列表，按相似度降序排序
        """
        try:

            embedding_string = ",".join(map(str, vector))

            vector_field = "name_vector" if property_key == "name" else ("desc_vector" if property_key == "desc" else "content_vector")

            query = f"""SELECT * FROM (SELECT id, name, node_id, label, properties, {vector_field}, 1 - ({vector_field} <=> '[{embedding_string}]'::vector) as score FROM {table} {f"WHERE label = %s" if node_type else ""}) WHERE score>%s ORDER BY score DESC LIMIT %s """
            
            # 准备参数
            params = []

            if node_type:
                params.append(node_type)

            params.extend([threshold, topk])

            # 执行查询
            results = self.sync_fetch(query, *params)
            # print(results)

            return results
            
        except Exception as e:
            logger.error(f"查找相似向量时出错: {str(e)}")
            raise

    def sync_get_entity_prop_by_id(self, id, node_type, table: str = "graph_nodes", ) -> List[Dict[str, Any]]:
        """
        使用余弦相似度查找最相近的向量
        
        Args:
            vector: 输入向量
            vector_field: 要比较的向量字段名称（name_vector 或 desc_vector）
            table: 要搜索的表名
            topk: 返回的最相近的前k
            
        Returns:
            最相似的记录列表，按相似度降序排序

            {'ids': ['a850774db1daed0fa9793b747d5ee39c550d501b73f450625d0d0f8e4682bfbb'],
            'project_id': '1',
            'spg_type': 'TwoWikiTest.Chunk'}

            SELECT * from graph_nodes WHERE label = `TwoWikiTest.Chunk` AND id = a850774db1daed0fa9793b747d5ee39c550d501b73f450625d0d0f8e4682bfbb

            SELECT * from graph_nodes WHERE label = 'TwoWikiTest.Chunk' AND node_id ='203dc45db8d288fb154a9454263a2390b8069f93a7b50b2f7ea4630e670a26ce';
        """
        try:



            query =f"SELECT * from  {table} WHERE label = %s AND node_id = %s"
            
            # 准备参数
            params = []

            node_label= node_type

            node_id = id

            params.extend([node_label, node_id])

            # 执行查询
            results = self.sync_fetch(query, *params)
            # print(results)

            return results
            
        except Exception as e:
            logger.error(f"查找相似向量时出错: {str(e)}")
            raise