# KAG MCP Server Example: BaiKe

[English](./mcp_server.md) |
[简体中文](./mcp_server_cn.md)

We have implemented an MCP server in KAG, allowing the knowledge base built by KAG to be exposed via the MCP server for integration with agents that support the MCP protocol.

## 1. Precondition

Please refer to [KAG Example: BaiKe](./README.md) to build the knowledge base and ensure the solver can produce answers successfully.

## 2. Launch the MCP server

Navigate to the directory containing the KAG project's configuration file [kag_config.yaml](./kag_config.yaml), then run the following command to launch the MCP server.

```bash
kag mcp-server
```

![Launch KAG MCP server](/_static/images/examples/baike/kag-launch-mcp-server.png)

By default, the KAG MCP server starts on port 3000 using Server‑Sent Events (SSE). You can use the ``--help`` option to view all the supported mcp-server options.

```bash
kag mcp-server --help
```

## 3. Configure Cursor to connect to the KAG MCP server

In Cursor, use the following configuration to connect to the KAG MCP server:

```json
{
    "mcpServers": {
        "kag": {
            "url": "http://127.0.0.1:3000/sse"
        }
    }
}
```

Restart Cursor and verify that the connection to the KAG MCP server is successful.

![Configure KAG MCP server in Cursor](/_static/images/examples/baike/kag-configure-in-cursor.png)

## 4. Test the KAG MCP Server in a Cursor Chat Session

Create a new chat session in Cursor and ask questions related to the knowledge base, for example:

```text
查询知识库回答：周星驰的姓名有何含义？
```

When you see the prompt ``Calling qa_pipeline``, click ``Run tool`` to execute the tool.

![Approve KAG MCP server call](/_static/images/examples/baike/kag-mcp-server-call-approve.png)

Below is a screenshot showing a successful invocation of the KAG MCP server.

![KAG MCP server call succeeded](/_static/images/examples/baike/kag-mcp-server-call-succeed.png)

