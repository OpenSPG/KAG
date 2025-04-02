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
            self, mcp_file_path, mcp_server_name, mcp_server_desc, llm_module: LLMClient, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = mcp_server_name
        self.desc = mcp_server_desc
        self.mcp_file_path = mcp_file_path
        self.llm_module = llm_module or LLMClient.from_config(
            KAG_CONFIG.all_config["chat_llm"]
        )
        self.mcp_client = MCPClient(llm_module)  # 在构造器中创建 MCPClient 的实例

    async def ainvoke(self, query, task, context: Context, **kwargs):
        await self.mcp_client.connect_to_server(self.mcp_file_path)
        response = await self.mcp_client.process_query(query)
        return response

    def schema(self, func_name: str = None) -> dict:
        """Function schema definition for OpenAI Function Calling

        Returns:
            dict: Schema definition in OpenAI Function format
        """
        return {
            "name": self.name,
            "description": self.desc,
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }