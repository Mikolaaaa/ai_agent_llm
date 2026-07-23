from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp_tool_server.contracts import PROTOCOL_VERSION, ServerContext
from mcp_tool_server.errors import MCPProtocolError, MCPToolExecutionError
from mcp_tool_server.server import JSONRPC_VERSION, MCPToolServer


@dataclass(slots=True)
class MCPClientResult:
    structured_content: dict[str, Any] | None
    content: list[dict[str, Any]]
    is_error: bool


class LocalMCPClient:
    """In-process MCP client for demos/tests.

    It uses the same JSON-RPC request/response shape as stdio/HTTP clients, but
    does not spawn a subprocess. This keeps the block 2 project easy to inspect.
    """

    def __init__(
        self,
        server: MCPToolServer | None = None,
        *,
        context: ServerContext | None = None,
    ) -> None:
        self.server = server or MCPToolServer()
        self.context = context or ServerContext.allow_all()
        self._next_id = 1

    async def initialize(self) -> dict[str, Any]:
        response = await self._request("initialize", {"protocolVersion": PROTOCOL_VERSION})
        return response["result"]

    async def info(self) -> dict[str, Any]:
        response = await self._request("server/info")
        return response["result"]

    async def list_tools(self) -> list[dict[str, Any]]:
        response = await self._request("tools/list")
        return response["result"]["tools"]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPClientResult:
        response = await self._request("tools/call", {"name": name, "arguments": arguments})
        result = response["result"]
        return MCPClientResult(
            structured_content=result.get("structuredContent"),
            content=result["content"],
            is_error=bool(result.get("isError", False)),
        )

    async def events(self) -> list[dict[str, Any]]:
        response = await self._request("events/list")
        return response["result"]["events"]

    async def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": self._next_id,
            "method": method,
        }
        self._next_id += 1
        if params is not None:
            request["params"] = params

        response = await self.server.handle(request, context=self.context)
        if response is None:
            raise MCPProtocolError("MCP request unexpectedly returned no response.")
        if "error" in response:
            data = response["error"].get("data", {})
            raise MCPProtocolError(
                response["error"]["message"],
                details={"jsonrpc_error": response["error"], "error_data": data},
            )
        return response


def raise_for_tool_error(result: MCPClientResult) -> dict[str, Any]:
    if not result.is_error:
        return result.structured_content or {}
    error = (result.structured_content or {}).get("error", {})
    raise MCPToolExecutionError(
        error.get("message", "MCP tool returned isError=true."),
        details={"mcp_error": error},
    )
