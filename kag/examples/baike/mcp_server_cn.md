# KAG MCP Server 示例：百科问答（BaiKe）

[English](./mcp_server.md) |
[简体中文](./mcp_server_cn.md)

我们在 KAG 中实现了 MCP server，可以将 KAG 构建的知识库通过 MCP server 的形式暴露出来，供支持 MCP 协议的 Agent 集成。

## 1. 前置条件

参考 [KAG 示例：百科问答（BaiKe）](./README_cn.md) 构建知识库并确保 solver 可正常产出问题答案。

## 2. 运行 MCP server

进入到 KAG 项目的配置文件 [kag_config.yaml](./kag_config.yaml) 在所在目录，执行以下命令启动 MCP server。

```bash
kag mcp-server
```

![Launch KAG MCP server](/_static/images/examples/baike/kag-launch-mcp-server.png)

KAG MCP server 默认以 sse 方式在端口 3000 启动服务。可使用 ``--help`` 选项查看 mcp-server 支持的选项。

```bash
kag mcp-server --help
```

## 3. 配置 Cursor 连接 KAG MCP server

在 Cursor 中使用以下配置连接 KAG MCP server。

```json
{
    "mcpServers": {
        "kag": {
            "url": "http://127.0.0.1:3000/sse"
        }
    }
}
```

重启 Cursor，确认 KAG MCP server 连接成功。

![Configure KAG MCP server in Cursor](/_static/images/examples/baike/kag-configure-in-cursor.png)

## 4. 测试在 Cursor 聊天会话中使用 KAG MCP server

新建 Cursor 聊天会话，询问知识库相关的问题，例如：

```text
查询知识库回答：周星驰的姓名有何含义？
```

当提示 ``Calling qa_pipeline`` 时，点 ``Run tool`` 运行工具。

![Approve KAG MCP server call](/_static/images/examples/baike/kag-mcp-server-call-approve.png)

以下是成功调用 KAG MCP server 的截图。

![KAG MCP server call succeeded](/_static/images/examples/baike/kag-mcp-server-call-succeed.png)

