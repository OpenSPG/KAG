from mcp.server.fastmcp import FastMCP

# 创建MCP服务器实例
mcp = FastMCP("mcp-server-web-search")


class InternetWebSearchTool:
    name = "web_search"
    description = """Performs an Internet web search based on your query (think a Google search) then returns the top search results."""
    inputs = {"query": {"type": "string", "description": "The search query to perform."}}
    output_type = "string"

    def __init__(self, max_results=10, **_kwargs):
        super().__init__()
        self.max_results = max_results

    def _web_search(self, query, max_results):
        """
        Args:
            query (str): The search query to perform.
            max_results (int): The maximum number of results to return.

        Returns:
            str: A string containing the top search results.
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
            "topk": max_results, # noqa
        }
        url = "https://spgservice-standard-gray.alipay.com/public/v1/search/text"
        res = requests.post(url, json=data, timeout=60)
        items = res.json()
        results = self._format_results(items)
        return results

    @classmethod
    def _format_results(cls, items):
        results = []
        for item in items:
            node = item["fields"]
            result = {
                "title": node["name"],
                "href": node["url"],
                "body": node["description"],
            }
            results.append(result)
        return results

    def forward(self, query: str) -> str:
        results = self._web_search(query=query, max_results=self.max_results)
        if len(results) == 0:
            raise Exception("No results found! Try a less restrictive/shorter query.")
        formatted_results = [f"[{result['title']}]({result['href']})\n{result['body']}" for result in results]
        return "## Search Results\n\n" + "\n\n".join(formatted_results)

@mcp.tool()
def web_search(query: str):
    search = InternetWebSearchTool()
    res = search.forward(query)
    print(res)
    return res

if __name__ == "__main__":
    web_search("天空为什么是蓝色的")
