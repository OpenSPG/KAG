import asyncio
import logging
import json
from pg_impl import PostgresDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def vector_search_demo():
    # 数据库配置
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "wr",
        "password": "your_password",
        "database": "test"
    }
    
    # 创建数据库连接
    db = PostgresDB(db_config)
    
    try:
        # 连接数据库
        await db.connect()
        
        # 1. 直接使用向量搜索
        # 假设我们有一个1024维的向量
        vector = [0.1] * 1024  # 这里简单示例，实际使用时应该是真实的向量
        
        # 搜索最相似的节点
        similar_nodes = await db.find_most_similar_vector(
            vector=vector,
            property_key="name",  # 使用name_vector字段
            table="graph_nodes",
            node_type = "TwoWikiTest.Person",
            threshold=-1,
            topk=1  # 返回前5个最相似的结果
        )
        
        # 打印结果
        logger.info("使用向量直接搜索的结果:")
        for node in similar_nodes:
            logger.info(f"节点ID: {node['node_id']}")
            logger.info(f"标签: {node['label']}")
            logger.info(f"相似度: {node['score']:.4f}")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
    finally:
        await db.close()

def sync_vector_search_demo():
    # 数据库配置
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "wr",
        "password": "your_password",
        "database": "test"
    }
    
    # 创建数据库连接
    db = PostgresDB(db_config)
    
    try:
        # 连接数据库
        db.sync_connect()
        
        # 1. 直接使用向量搜索
        # 假设我们有一个1024维的向量
        vector = [0.1] * 1024  # 这里简单示例，实际使用时应该是真实的向量
        
        # 搜索最相似的节点
        similar_nodes = db.sync_find_most_similar_vector(
            vector=vector,
            property_key="content",  # 使用name_vector字段
            table="graph_nodes",
            node_type = "TwoWikiTest.Chunk",
            threshold=-1,
            topk=1  # 返回前5个最相似的结果
        )
        
        # 打印结果
        logger.info("使用向量直接搜索的结果:")
        for node in similar_nodes:
            logger.info(f"节点ID: {node['node_id']}")
            logger.info(f"标签: {node['label']}")
            logger.info(f"相似度: {node['score']:.4f}")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
    finally:
        db.sync_close()

if __name__ == "__main__":
    # asyncio.run(vector_search_demo()) 
    sync_vector_search_demo()