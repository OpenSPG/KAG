from kag.common.conf import KAG_CONFIG
from kag.interface import ExecutorABC
import asyncio


async def chat_loop(client):
    """Run an interactive chat loop"""
    print("\nMCP Client Started!")
    print("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == "quit":
                break

            from kag.interface import Task, Context

            task = Task("mcp", arguments={"query": query})
            response = await client.ainvoke(query, task, Context())
            print("\n" + response)

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"\nError: {str(e)}")


async def cleanup(client):
    """Clean up resources"""
    await client.mcp_client.exit_stack.aclose()


async def main():
    server_script_path = "./map.py"
    executor = ExecutorABC.from_config(KAG_CONFIG.all_config["mcp_executor"])
    client = executor

    try:
        print(f"executor.env = {executor.env}")
        await chat_loop(client)
    finally:
        await cleanup(client)


if __name__ == "__main__":
    asyncio.run(main())
