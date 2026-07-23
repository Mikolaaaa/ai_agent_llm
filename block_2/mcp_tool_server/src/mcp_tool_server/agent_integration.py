from __future__ import annotations

from typing import Any

from mcp_tool_server.client import LocalMCPClient


async def build_mcp_proxy_registry(client: LocalMCPClient):
    """Build block 1 ToolRegistry where handlers proxy calls to an MCP server.

    This is intentionally an adapter layer. Agent runtime stays responsible for
    the model loop, state and policy; MCP server stays responsible for tool
    contracts and execution.
    """
    from agent_runtime.core.errors import (
        DependencyRuntimeError,
        PermissionRuntimeError,
        ToolNotFoundRuntimeError,
        ValidationRuntimeError,
    )
    from agent_runtime.tools.registry import ToolDefinition, ToolRegistry

    def make_handler(tool_name: str):
        async def handler(arguments: dict[str, Any]) -> dict[str, Any]:
            result = await client.call_tool(tool_name, arguments)
            if not result.is_error:
                return result.structured_content or {}

            error = (result.structured_content or {}).get("error", {})
            message = error.get("message", "MCP tool returned an error.")
            if error.get("retryable"):
                raise DependencyRuntimeError(message, details={"mcp_error": error})
            if error.get("type") == "permission_error":
                raise PermissionRuntimeError(message, details={"mcp_error": error})
            if error.get("type") == "tool_not_found":
                raise ToolNotFoundRuntimeError(message, details={"mcp_error": error})
            raise ValidationRuntimeError(message, details={"mcp_error": error})

        return handler

    registry = ToolRegistry()
    for tool in await client.list_tools():
        runtime_meta = tool.get("x-runtime", {})
        registry.register(
            ToolDefinition(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["inputSchema"],
                output_schema=tool["outputSchema"],
                required_scopes=set(runtime_meta.get("required_scopes", [])),
                retryable=bool(runtime_meta.get("retryable", False)),
                side_effect=bool(runtime_meta.get("side_effect", False)),
                timeout_seconds=runtime_meta.get("timeout_seconds"),
                handler=make_handler(tool["name"]),
                metadata={"source": "mcp", "mcp_tool": tool},
            )
        )
    return registry
