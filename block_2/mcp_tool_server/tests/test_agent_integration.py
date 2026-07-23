from __future__ import annotations

import unittest

from agent_runtime.core.state import Principal
from agent_runtime.engine.runtime import AgentRuntime
from agent_runtime.model.fake import FinalAnswer, ScriptedFakeModel, ToolCallRequest

from mcp_tool_server.core.contracts import ServerContext
from mcp_tool_server.integration.agent_runtime import build_mcp_proxy_registry
from mcp_tool_server.mcp.client import LocalMCPClient
from mcp_tool_server.mcp.server import MCPToolServer


class AgentIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_runtime_calls_mcp_tool_and_completes(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext(
                trace_id="trace_agent_mcp",
                allowed_tools={"search_documents"},
                scopes={"documents.read"},
            ),
        )
        registry = await build_mcp_proxy_registry(client)
        runtime = AgentRuntime(
            model=ScriptedFakeModel(
                [
                    ToolCallRequest(
                        tool_name="search_documents",
                        arguments={"query": "mcp", "limit": 2},
                    ),
                    FinalAnswer("MCP result was used."),
                ]
            ),
            registry=registry,
        )

        state = await runtime.run(
            "find mcp docs",
            principal=Principal(user_id="user_1", scopes={"documents.read"}),
            allowed_tools={"search_documents"},
        )

        self.assertEqual(state.status.value, "completed")
        self.assertEqual(state.final_answer, "MCP result was used.")
        self.assertEqual(state.tool_results[0].tool_name, "search_documents")
        self.assertIn("documents", state.tool_results[0].output)

    async def test_agent_runtime_maps_mcp_tool_error_to_failed_run(self) -> None:
        client = LocalMCPClient(
            MCPToolServer(),
            context=ServerContext(
                trace_id="trace_agent_mcp_error",
                allowed_tools={"unstable_dependency"},
                scopes={"debug.use"},
            ),
        )
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
            "call unstable dependency",
            principal=Principal(user_id="user_1", scopes={"debug.use"}),
            allowed_tools={"unstable_dependency"},
        )

        self.assertEqual(state.status.value, "failed")
        self.assertEqual(state.error.code, "dependency_error")
