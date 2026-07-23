from __future__ import annotations

import unittest

from mcp_tool_server.core.contracts import ServerContext
from mcp_tool_server.mcp.client import LocalMCPClient
from mcp_tool_server.mcp.server import MCPToolServer


class ServerClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_info_and_tools_list(self) -> None:
        client = LocalMCPClient()

        info = await client.info()
        tools = await client.list_tools()

        self.assertEqual(info["name"], "block-2-mcp-tool-server")
        self.assertGreaterEqual(info["tools_count"], 4)
        self.assertIn("search_documents", {tool["name"] for tool in tools})

    async def test_direct_tool_call_happy_path(self) -> None:
        client = LocalMCPClient()

        result = await client.call_tool("search_documents", {"query": "mcp", "limit": 2})

        self.assertFalse(result.is_error)
        self.assertIsNotNone(result.structured_content)
        self.assertIn("documents", result.structured_content)

    async def test_get_user_context_happy_path(self) -> None:
        client = LocalMCPClient()

        result = await client.call_tool("get_user_context", {"user_id": "user_1"})

        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["active_block"], "block_2_mcp")

    async def test_invalid_arguments_return_tool_error_result(self) -> None:
        client = LocalMCPClient()

        result = await client.call_tool("search_documents", {"query": "", "limit": 100})

        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content["error"]["type"], "validation_error")

    async def test_trace_logs_are_recorded_for_tool_call(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext.allow_all(trace_id="trace_test_123"),
        )

        await client.call_tool("calculate_metric", {"values": [1, 2, 3], "metric": "sum"})
        events = await client.events()

        self.assertTrue(events)
        self.assertTrue(all(event["trace_id"] == "trace_test_123" for event in events))
        self.assertIn("mcp_tool_call_started", {event["name"] for event in events})
        self.assertIn("mcp_tool_call_finished", {event["name"] for event in events})
