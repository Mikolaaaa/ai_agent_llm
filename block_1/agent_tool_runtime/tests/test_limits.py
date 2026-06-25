import unittest

from agent_runtime.core.state import Principal, RunLimits, RunStatus
from agent_runtime.model.fake import ScriptedFakeModel, ToolCallRequest
from agent_runtime.engine.runtime import AgentRuntime


class LimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_max_iterations_exceeded(self) -> None:
        model = ScriptedFakeModel(
            [
                ToolCallRequest("search_documents", {"query": "agent", "top_k": 1}),
                ToolCallRequest("search_documents", {"query": "agent", "top_k": 1}),
            ]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "loop",
            principal=Principal(user_id="u1", scopes={"documents.read"}),
            allowed_tools={"search_documents"},
            limits=RunLimits(max_iterations=1),
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.error.type.value, "limit_error")

    async def test_max_tool_calls_exceeded(self) -> None:
        model = ScriptedFakeModel(
            [
                ToolCallRequest("search_documents", {"query": "agent", "top_k": 1}),
                ToolCallRequest("search_documents", {"query": "agent", "top_k": 1}),
            ]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "loop",
            principal=Principal(user_id="u1", scopes={"documents.read"}),
            allowed_tools={"search_documents"},
            limits=RunLimits(max_iterations=5, max_tool_calls=1),
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.error.type.value, "limit_error")


if __name__ == "__main__":
    unittest.main()
