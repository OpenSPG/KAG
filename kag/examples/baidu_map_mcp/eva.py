from kag.solver.executor.mcp.mcp_client import MCPClient
import asyncio


async def chat_loop(client):
    """Run an interactive chat loop"""
    print("\nMCP Client Started!")
    print("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            response = await client.process_query(query)
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")


async def cleanup(client):
    """Clean up resources"""
    await client.exit_stack.aclose()


async def main():
    server_script_path = "./map.py"
    client = MCPClient()
    try:
        await client.connect_to_server(server_script_path)
        await chat_loop(client)
    finally:
        await cleanup(client)


if __name__ == "__main__":
    asyncio.run(main())
