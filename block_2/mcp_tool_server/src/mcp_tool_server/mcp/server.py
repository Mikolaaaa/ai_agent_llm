from __future__ import annotations

import asyncio
import json
import sys
from time import perf_counter
from typing import Any

from mcp_tool_server.core.contracts import (
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    MCPToolCallResult,
    ServerContext,
)
from mcp_tool_server.core.errors import (
    MCPErrorInfo,
    MCPProtocolError,
    MCPServerError,
    MCPTimeoutError,
    map_exception,
)
from mcp_tool_server.core.events import InMemoryEventSink
from mcp_tool_server.core.permissions import assert_tool_allowed
from mcp_tool_server.tools.registry import ToolRegistry, build_default_registry


JSONRPC_VERSION = "2.0"


class MCPToolServer:
    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        events: InMemoryEventSink | None = None,
        name: str = "block-2-mcp-tool-server",
        version: str = "0.1.0",
    ) -> None:
        self.registry = registry or build_default_registry()
        self.events = events or InMemoryEventSink()
        self.name = name
        self.version = version

    async def handle(
        self,
        request: dict[str, Any],
        *,
        context: ServerContext | None = None,
    ) -> dict[str, Any] | None:
        context = context or ServerContext.allow_all()
        request_id = request.get("id") if isinstance(request, dict) else None
        try:
            self._validate_request(request)
            method = request["method"]
            params = request.get("params") or {}

            if method == "notifications/initialized" and request_id is None:
                self.events.emit("mcp_initialized", trace_id=context.trace_id)
                return None
            if method == "initialize":
                return self._success(request_id, self._initialize_result(params))
            if method == "server/info":
                return self._success(request_id, self._info_result())
            if method == "tools/list":
                return self._success(request_id, {"tools": self.registry.list_mcp_tools()})
            if method == "tools/call":
                result = await self._call_tool(params, context=context)
                return self._success(request_id, result.to_mcp_result())
            if method == "events/list":
                return self._success(request_id, {"events": self.events.list()})

            raise MCPProtocolError(f"Unknown MCP method '{method}'.", details={"method": method})
        except MCPProtocolError as exc:
            return self._error(request_id, code=-32601, error=exc.to_info())
        except MCPServerError as exc:
            return self._error(request_id, code=-32602, error=exc.to_info())
        except BaseException as exc:
            return self._error(request_id, code=-32000, error=map_exception(exc))

    async def _call_tool(self, params: dict[str, Any], *, context: ServerContext) -> MCPToolCallResult:
        if not isinstance(params, dict):
            raise MCPProtocolError("tools/call params must be an object.")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not name:
            raise MCPProtocolError("tools/call params.name must be a non-empty string.")
        if not isinstance(arguments, dict):
            raise MCPProtocolError("tools/call params.arguments must be an object.")

        tool = self.registry.get(name)
        started = perf_counter()
        self.events.emit(
            "mcp_tool_call_started",
            trace_id=context.trace_id,
            data={"tool_name": tool.name},
        )
        try:
            assert_tool_allowed(tool, context)
            valid_args = tool.validate_input(arguments)
            output = await asyncio.wait_for(tool.handler(valid_args), timeout=tool.timeout_seconds)
            valid_output = tool.validate_output(output)
            duration_ms = round((perf_counter() - started) * 1000, 2)
            self.events.emit(
                "mcp_tool_call_finished",
                trace_id=context.trace_id,
                data={"tool_name": tool.name, "ok": True, "duration_ms": duration_ms},
            )
            return MCPToolCallResult(
                content=[{"type": "text", "text": json.dumps(valid_output, ensure_ascii=False)}],
                structured_content=valid_output,
                is_error=False,
            )
        except asyncio.TimeoutError as exc:
            error = MCPTimeoutError(
                f"Tool '{tool.name}' exceeded timeout.",
                details={"tool_name": tool.name, "timeout_seconds": tool.timeout_seconds},
            ).to_info()
            self._emit_tool_error(context, tool.name, error, started)
            return _tool_error_result(error)
        except BaseException as exc:
            error = map_exception(exc)
            self._emit_tool_error(context, tool.name, error, started)
            return _tool_error_result(error)

    def _emit_tool_error(
        self,
        context: ServerContext,
        tool_name: str,
        error: MCPErrorInfo,
        started: float,
    ) -> None:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        self.events.emit(
            "mcp_tool_call_finished",
            trace_id=context.trace_id,
            data={
                "tool_name": tool_name,
                "ok": False,
                "duration_ms": duration_ms,
                "error": error.to_dict(),
            },
        )

    def _initialize_result(self, params: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise MCPProtocolError("initialize params must be an object.")

        requested_version = params.get("protocolVersion", PROTOCOL_VERSION)
        if requested_version not in SUPPORTED_PROTOCOL_VERSIONS:
            raise MCPProtocolError(
                "Unsupported MCP protocol version.",
                details={
                    "requested_protocol_version": requested_version,
                    "supported_protocol_versions": sorted(SUPPORTED_PROTOCOL_VERSIONS),
                },
            )

        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _info_result(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": PROTOCOL_VERSION,
            "tools_count": len(self.registry.list()),
        }

    def _validate_request(self, request: dict[str, Any]) -> None:
        if not isinstance(request, dict):
            raise MCPProtocolError("JSON-RPC request must be an object.")
        if request.get("jsonrpc") != JSONRPC_VERSION:
            raise MCPProtocolError("JSON-RPC version must be '2.0'.")
        if "method" not in request or not isinstance(request["method"], str):
            raise MCPProtocolError("JSON-RPC request.method must be a string.")

    def _success(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _error(self, request_id: Any, *, code: int, error: MCPErrorInfo) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {
                "code": code,
                "message": error.message,
                "data": error.to_dict(),
            },
        }


def _tool_error_result(error: MCPErrorInfo) -> MCPToolCallResult:
    return MCPToolCallResult(
        content=[{"type": "text", "text": error.message}],
        structured_content={"error": error.to_dict()},
        is_error=True,
    )


async def run_stdio_server() -> None:
    server = MCPToolServer()
    context = ServerContext.allow_all(trace_id="trace_stdio")
    for line in sys.stdin:
        if not line.strip():
            continue
        response = await server.handle(json.loads(line), context=context)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def main() -> None:
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
