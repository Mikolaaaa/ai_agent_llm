from __future__ import annotations

import unittest

from mcp_tool_server.core.errors import MCPContractError
from mcp_tool_server.tools.registry import build_default_registry, build_incompatible_registry


class ContractTests(unittest.TestCase):
    def test_default_registry_exposes_valid_mcp_contracts(self) -> None:
        registry = build_default_registry()

        tools = registry.list_mcp_tools()

        self.assertGreaterEqual(len(tools), 6)
        self.assertGreaterEqual(
            {tool["name"] for tool in tools},
            {
                "search_documents",
                "get_document",
                "save_note",
                "calculate_metric",
                "get_user_context",
            },
        )
        for tool in tools:
            self.assertTrue(tool["description"])
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertEqual(tool["outputSchema"]["type"], "object")
            self.assertIn("x-runtime", tool)

    def test_incompatible_schema_is_rejected(self) -> None:
        with self.assertRaises(MCPContractError):
            build_incompatible_registry()
