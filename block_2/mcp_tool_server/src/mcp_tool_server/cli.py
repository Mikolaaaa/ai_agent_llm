from __future__ import annotations

import argparse
import asyncio
import json

from mcp_tool_server.client import LocalMCPClient
from mcp_tool_server.contracts import ServerContext
from mcp_tool_server.server import MCPToolServer


async def _list_tools(args: argparse.Namespace) -> None:
    client = _client(args)
    tools = await client.list_tools()
    print(json.dumps({"tools": tools}, ensure_ascii=False, indent=2))


async def _call_tool(args: argparse.Namespace) -> None:
    client = _client(args)
    arguments = json.loads(args.arguments)
    result = await client.call_tool(args.name, arguments)
    print(
        json.dumps(
            {
                "is_error": result.is_error,
                "structured_content": result.structured_content,
                "content": result.content,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


async def _info(args: argparse.Namespace) -> None:
    client = _client(args)
    print(json.dumps(await client.info(), ensure_ascii=False, indent=2))


async def _events(args: argparse.Namespace) -> None:
    client = _client(args)
    await client.call_tool("search_documents", {"query": "mcp", "limit": 2})
    print(json.dumps(await client.events(), ensure_ascii=False, indent=2))


async def _agent_demo(args: argparse.Namespace) -> None:
    from agent_runtime.core.state import Principal
    from agent_runtime.engine.runtime import AgentRuntime
    from agent_runtime.model.fake import FinalAnswer, ScriptedFakeModel, ToolCallRequest

    from mcp_tool_server.agent_integration import build_mcp_proxy_registry

    client = _client(args)
    registry = await build_mcp_proxy_registry(client)
    runtime = AgentRuntime(
        model=ScriptedFakeModel(
            [
                ToolCallRequest(
                    tool_name="search_documents",
                    arguments={"query": "mcp", "limit": 2},
                ),
                FinalAnswer("Agent used MCP search_documents and produced a final answer."),
            ]
        ),
        registry=registry,
    )
    state = await runtime.run(
        "find mcp docs",
        principal=Principal(user_id="demo_user", scopes={"documents.read"}),
        allowed_tools={"search_documents"},
    )
    print(
        json.dumps(
            {
                "status": state.status.value,
                "final_answer": state.final_answer,
                "tool_results": [result.to_dict() for result in state.tool_results],
                "summary": state.summary().to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


async def _agent_error_demo(args: argparse.Namespace) -> None:
    from agent_runtime.core.state import Principal
    from agent_runtime.engine.runtime import AgentRuntime
    from agent_runtime.model.fake import ScriptedFakeModel, ToolCallRequest

    from mcp_tool_server.agent_integration import build_mcp_proxy_registry

    client = _client(args)
    registry = await build_mcp_proxy_registry(client)
    runtime = AgentRuntime(
        model=ScriptedFakeModel(
            [
                ToolCallRequest(tool_name="unstable_dependency", arguments={}),
            ]
        ),
        registry=registry,
    )
    state = await runtime.run(
        "call unstable MCP dependency",
        principal=Principal(user_id="demo_user", scopes={"debug.use"}),
        allowed_tools={"unstable_dependency"},
    )
    print(
        json.dumps(
            {
                "status": state.status.value,
                "error": state.error.to_dict() if state.error else None,
                "summary": state.summary().to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _client(args: argparse.Namespace) -> LocalMCPClient:
    scopes = set(args.scopes.split(",")) if args.scopes else {"*"}
    allowed_tools = set(args.allowed_tools.split(",")) if args.allowed_tools else {"*"}
    confirmations = set(args.confirmations.split(",")) if args.confirmations else set()
    return LocalMCPClient(
        MCPToolServer(),
        context=ServerContext(
            trace_id=args.trace_id,
            scopes=scopes,
            allowed_tools=allowed_tools,
            confirmations=confirmations,
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Block 2 MCP Tool Server demo CLI")
    parser.add_argument("--trace-id", default="trace_cli")
    parser.add_argument("--scopes", default="*")
    parser.add_argument("--allowed-tools", default="*")
    parser.add_argument("--confirmations", default="")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info").set_defaults(func=_info)
    sub.add_parser("list-tools").set_defaults(func=_list_tools)

    call = sub.add_parser("call-tool")
    call.add_argument("name")
    call.add_argument("arguments")
    call.set_defaults(func=_call_tool)

    sub.add_parser("events-demo").set_defaults(func=_events)
    sub.add_parser("agent-demo").set_defaults(func=_agent_demo)
    sub.add_parser("agent-error-demo").set_defaults(func=_agent_error_demo)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
