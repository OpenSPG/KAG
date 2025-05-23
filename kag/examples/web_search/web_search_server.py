from mcp.server.fastmcp import FastMCP

# 创建MCP服务器实例
mcp = FastMCP("mcp-server-web-search")


@mcp.tool()
async def web_search(query: str):
    """
    Name:
        Google搜索

    Description:
        通过输入问题，获取对应Google搜索的结果

    Args:
        query: 问题描述
    """
    import requests

    channel = "google"
    dummy_project_id = -1
    data = {
        "params": {
            "search_online_enabled": "yes",
            "uid": "2088312789426949",
            "staff_number": "000000",
            "search_engine": channel,
        },
        "projectId": dummy_project_id,
        "queryString": query,
        "topk": 3,  # noqa
    }
    url = "https://spgservice-standard-gray.alipay.com/public/v1/search/text"
    res = requests.post(url, json=data, timeout=60)
    items = res.json()

    results = []
    for item in items:
        node = item["fields"]
        result = {
            "title": node["name"],
            "href": node["url"],
            "body": node["description"],
        }
        results.append(result)

    if len(results) == 0:
        raise Exception("No results found! Try a less restrictive/shorter query.")
    formatted_results = [
        f"[{result['title']}]({result['href']})\n{result['body']}" for result in results
    ]
    return "## Search Results\n\n" + "\n\n".join(formatted_results)


async def main():
    result = await web_search("天空为什么是蓝色的")
    print(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
    # import asyncio
    # asyncio.run(main())
