from __future__ import annotations

from mcp_tool_server.contracts import ServerContext, ToolContract
from mcp_tool_server.errors import MCPPermissionError


def assert_tool_allowed(tool: ToolContract, context: ServerContext) -> None:
    if "*" not in context.allowed_tools and tool.name not in context.allowed_tools:
        raise MCPPermissionError(
            f"Tool '{tool.name}' is not allowed for this MCP call.",
            details={"tool_name": tool.name, "allowed_tools": sorted(context.allowed_tools)},
        )

    if "*" not in context.scopes:
        missing = sorted(tool.required_scopes - context.scopes)
        if missing:
            raise MCPPermissionError(
                f"Missing scopes for tool '{tool.name}'.",
                details={"tool_name": tool.name, "missing_scopes": missing},
            )

    if tool.side_effect and "*" not in context.confirmations and tool.name not in context.confirmations:
        raise MCPPermissionError(
            f"Tool '{tool.name}' has side effects and requires confirmation.",
            details={"tool_name": tool.name},
        )

