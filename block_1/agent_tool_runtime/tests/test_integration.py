import unittest
from typing import Any

from agent_runtime.core.state import Principal, RunLimits, RunStatus
from agent_runtime.observability.events import InMemoryEventSink
from agent_runtime.model.fake import FinalAnswer, ScriptedFakeModel, ToolCallRequest
from agent_runtime.tools.registry import ToolDefinition, ToolRegistry
from agent_runtime.engine.runtime import AgentRuntime


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_happy_path(self) -> None:
        events = InMemoryEventSink()
        model = ScriptedFakeModel(
            [
                ToolCallRequest("search_documents", {"query": "runtime", "top_k": 2}),
                FinalAnswer("Found runtime docs."),
            ]
        )
        runtime = AgentRuntime(model=model, events=events)

        state = await runtime.run(
            "find runtime docs",
            principal=Principal(user_id="u1", scopes={"documents.read"}),
            allowed_tools={"search_documents"},
            limits=RunLimits(max_iterations=4),
        )

        self.assertEqual(state.status, RunStatus.COMPLETED)
        self.assertEqual(state.final_answer, "Found runtime docs.")
        self.assertEqual(state.iterations, 2)
        self.assertEqual(len(state.tool_calls), 1)
        self.assertEqual(len(state.tool_results), 1)
        self.assertTrue(state.tool_results[0].ok)
        self.assertTrue(all(event["trace_id"] == state.trace_id for event in events.events))
        self.assertEqual(state.summary().terminal_reason, "completed")

    async def test_invalid_tool_arguments_fail_run(self) -> None:
        model = ScriptedFakeModel(
            [ToolCallRequest("search_documents", {"query": "", "top_k": 100})]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "bad args",
            principal=Principal(user_id="u1", scopes={"documents.read"}),
            allowed_tools={"search_documents"},
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.error.type.value, "validation_error")
        self.assertEqual(len(state.tool_calls), 0)

    async def test_permission_error_happens_before_tool_execution(self) -> None:
        model = ScriptedFakeModel(
            [ToolCallRequest("save_note", {"title": "x", "content": "y"})]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "save note",
            principal=Principal(user_id="u1", scopes={"notes.write"}),
            allowed_tools={"search_documents"},
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.error.type.value, "permission_error")
        self.assertEqual(len(state.tool_calls), 0)

    async def test_retryable_tool_retries_then_succeeds(self) -> None:
        model = ScriptedFakeModel(
            [
                ToolCallRequest("flaky_status", {}),
                FinalAnswer("status ok"),
            ]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "status",
            principal=Principal(user_id="u1", scopes={"status.read"}),
            allowed_tools={"flaky_status"},
            limits=RunLimits(max_iterations=3, max_retries=1),
        )
        self.assertEqual(state.status, RunStatus.COMPLETED)
        self.assertEqual(state.tool_calls[0].attempts, 2)

    async def test_timeout_error_fails_run(self) -> None:
        model = ScriptedFakeModel(
            [ToolCallRequest("slow_tool", {"sleep_seconds": 0.05})]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "slow",
            principal=Principal(user_id="u1", scopes={"debug.use"}),
            allowed_tools={"slow_tool"},
            limits=RunLimits(max_iterations=2, max_retries=0),
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.tool_results[0].error.type.value, "timeout_error")

    async def test_invalid_tool_output_fails_run(self) -> None:
        async def bad_handler(args: dict[str, Any]) -> dict[str, Any]:
            return {"unexpected": "shape"}

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="bad_output",
                description="Returns invalid output for testing.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                output_schema={
                    "type": "object",
                    "required": ["ok"],
                    "additionalProperties": False,
                    "properties": {"ok": {"type": "boolean"}},
                },
                required_scopes={"debug.use"},
                handler=bad_handler,
            )
        )
        model = ScriptedFakeModel([ToolCallRequest("bad_output", {})])
        runtime = AgentRuntime(model=model, registry=registry)
        state = await runtime.run(
            "bad output",
            principal=Principal(user_id="u1", scopes={"debug.use"}),
            allowed_tools={"bad_output"},
        )
        self.assertEqual(state.status, RunStatus.FAILED)
        self.assertEqual(state.tool_results[0].error.type.value, "validation_error")


if __name__ == "__main__":
    unittest.main()
