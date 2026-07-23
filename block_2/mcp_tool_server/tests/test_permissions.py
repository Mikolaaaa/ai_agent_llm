from __future__ import annotations

import unittest

from mcp_tool_server.client import LocalMCPClient
from mcp_tool_server.contracts import ServerContext
from mcp_tool_server.server import MCPToolServer


class PermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_forbidden_tool_is_explicit_error(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext(
                trace_id="trace_permissions",
                allowed_tools={"search_documents"},
                scopes={"documents.read"},
            ),
        )

        result = await client.call_tool("save_note", {"title": "x", "content": "y"})

        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content["error"]["type"], "permission_error")

    async def test_side_effect_tool_requires_confirmation(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext(
                trace_id="trace_confirmation",
                allowed_tools={"save_note"},
                scopes={"notes.write"},
                confirmations=set(),
            ),
        )

        result = await client.call_tool("save_note", {"title": "x", "content": "y"})

        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content["error"]["type"], "permission_error")

    async def test_side_effect_tool_succeeds_with_confirmation(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext(
                trace_id="trace_confirmation_ok",
                allowed_tools={"save_note"},
                scopes={"notes.write"},
                confirmations={"save_note"},
            ),
        )

        result = await client.call_tool("save_note", {"title": "x", "content": "y"})

        self.assertFalse(result.is_error)
        self.assertTrue(result.structured_content["saved"])

