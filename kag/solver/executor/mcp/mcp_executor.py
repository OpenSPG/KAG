from kag.common.conf import KAG_CONFIG
import json
import logging

from typing import Any
from dotenv import load_dotenv
from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import ExecutorABC, LLMClient, Context
from kag.solver.utils import init_prompt_with_fallback
from typing import (
    TYPE_CHECKING,
)

from mcp_client import MCPClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger()


@ExecutorABC.register("mcp_executor")
class McpExecutor(ExecutorABC):
    def __init__(
            self, json_file_path, llm_module: LLMClient = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.file_path = json_file_path
        self.solve_question_without_spo_prompt = init_prompt_with_fallback(
            "summary_question", KAG_PROJECT_CONF.biz_scene
        )
        self.llm_module = llm_module or LLMClient.from_config(
            KAG_CONFIG.all_config["chat_llm"]
        )
        self.mcp_client = MCPClient()  # 在构造器中创建 MCPClient 的实例

    async def ainvoke(self, server_name, query, **kwargs):
        mcp_server_info = self.mcp_client.get_mcp_server(server_name)
        await self.mcp_client.connect_to_server(mcp_server_info['mcp_file'])
        response = await self.mcp_client.process_query(query)
        return response

    def schema(self, server_info) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        self.mcp_client.get_mcp_servers()
        # 构造 JSON 格式的内容
        mcp_schema_data = {
            "available_servers": [
                {"name": server["name"], "desc": server["desc"]}
                for server in server_info
            ]
        }
        return mcp_schema_data
