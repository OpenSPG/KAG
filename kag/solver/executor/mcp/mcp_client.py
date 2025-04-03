import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import (
    TYPE_CHECKING,
    Optional,
)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from kag.interface import LLMClient

if TYPE_CHECKING:
    pass

llm_config = {
    "api_key": '',
    "base_url": 'https://api.deepseek.com',
    'model': 'deepseek-chat',
    'type': 'maas'
}


class MCPClient:
    def __init__(self, llm: LLMClient):
        """初始化 MCP 客户端"""
        self.exit_stack = AsyncExitStack()
        # self.openai_api_key = llm_config["api_key"]  # 读取 OpenAI API Key
        # self.base_url = llm_config["base_url"]  # 读取 BASE YRL
        # self.model = llm_config["model"]  # 读取 model
        # if not self.openai_api_key:
        #     raise ValueError("未找到 OpenAI API Key")
        # self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)  # 创建OpenAI client
        self.client = llm
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "system",
                "content": """在这个环境中，你可以使用一系列工具来回答用户的问题。
                    你可以通过编写形如以下的 <tool_calls> 块来调用函数：
                    <tool_calls>
                    <tool_call id="call_1">
                    <tool_name>tool_name</tool_name>
                    <parameters>
                    {"param1": "value1", "param2": "value2"}
                    </parameters>
                    </tool_call>
                    </tool_calls>
                    
                    以下是可用的工具：
                    {
                      "tools": [
                        {
                          "name": "search_web",
                          "description": "搜索互联网获取信息",
                          "parameters": {
                            "query": "搜索查询内容"
                          }
                        },
                        {
                          "name": "get_weather",
                          "description": "获取特定地点的天气信息",
                          "parameters": {
                            "location": "地点名称",
                            "unit": "温度单位 (celsius 或 fahrenheit)"
                          }
                        }
                      ]
                    }
                    
                    使用工具时，请遵循以下步骤：
                    1. 分析用户查询，确定需要使用的工具
                    2. 使用上述格式调用适当的工具
                    3. 等待工具返回结果
                    4. 基于工具结果回答用户的问题 
                    如果工具返回结果不足以回答用户问题，你可以进行多次工具调用。
                    如果不需要使用任何工具就能回答用户问题，直接回答即可，无需进行工具调用。"""
            },
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
        } for tool in response.tools]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools
        )

        # 处理返回的内容
        content = response.choices[0]
        if content.finish_reason == "tool_calls":
            # 如果是需要使用工具，就解析工具
            tool_call = content.message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # 执行工具
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")

            # 将模型返回的调用哪个工具数据和工具执行完成后的数据都存入messages中
            tool_calls_message = content.message.model_dump()
            messages.append(tool_calls_message)
            messages.append({
                "role": "tool",
                "content": result.content[0].text,
                "tool_call_id": tool_call.id
            })
            # 将上面的结果再返回给大模型用于生产最终的结果
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content

        return content.message.content

    def extract_all_servers_info(self, mcp_file_path):
        """
        提取所有服务器的 `API_KEY`、`store_path` 和 `description`。
        Returns:
            一个字典，包含每个服务器的相关信息。
        """
        try:
            # 读取 JSON 文件内容
            with open(mcp_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # 初始化结果存储字典
            extracted_info = {}

            # 遍历所有服务器
            for server_name, server_data in data.items():
                env = server_data.get("env", {})
                api_keys = list(env.values())  # 提取环境变量中的所有 API_KEY（通常只会有一个）
                extracted_info[server_name] = {
                    "API_KEY": api_keys[0] if api_keys else "",
                    "store_path": server_data.get("store_path", ""),
                    "description": server_data.get("description", "")
                }

            return extracted_info

        except FileNotFoundError:
            print(f"文件未找到：{mcp_file_path}")
            return None
        except json.JSONDecodeError:
            print("JSON 文件解析错误，请检查内容格式是否正确。")
            return None
        except Exception as e:
            print(f"发生错误：{e}")
            return None

    def get_mcp_server(self, server_name: str, json_file_path: str):
        """
        根据 server_name 从 mcp.json 获取对应的 api_key 和 mcp_file。
        :param json_file_path: mcp.json 文件路径
        :param server_name: 要查找的服务器名称
        :return: 包含 api_key 和 mcp_file 的字典，如果未找到则返回 None
        """
        try:
            # 读取 JSON 文件内容
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # 查找指定服务器
            servers = data.get("mcpServers", {})
            server_data = servers.get(server_name)

            if not server_data:
                print(f"未找到服务器：{server_name}")
                return None

            # 提取 API_KEY 和 store_path
            api_key = list(server_data.get("env", {}).values())[0] if server_data.get("env", {}) else ""
            store_path = server_data.get("store_path", "")

            return {
                "API_KEY": api_key,
                "store_path": store_path
            }

        except FileNotFoundError:
            print(f"文件未找到：{json_file_path}")
            return None
        except json.JSONDecodeError:
            print("JSON 文件解析错误，请检查内容格式是否正确。")
            return None
        except Exception as e:
            print(f"发生错误：{e}")
            return None