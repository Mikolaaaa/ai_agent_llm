import unittest
from uuid import uuid4
from typing import Any

from agent_runtime.core.state import Principal, RunLimits, RunStatus
from agent_runtime.core.errors import ValidationRuntimeError
from agent_runtime.observability.events import InMemoryEventSink
from agent_runtime.model.fake import FinalAnswer, ScriptedFakeModel, ToolCallRequest
from agent_runtime.storage.sqlite import SQLiteRunStore
from agent_runtime.tools.builtin import reset_demo_state, save_note
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

    async def test_confirmed_side_effect_tool_succeeds(self) -> None:
        reset_demo_state()
        key = f"test-key-{uuid4().hex}"
        model = ScriptedFakeModel(
            [
                ToolCallRequest(
                    "save_note",
                    {"title": "Runtime", "content": "Side effect confirmed", "idempotency_key": key},
                ),
                FinalAnswer("saved"),
            ]
        )
        runtime = AgentRuntime(model=model)
        state = await runtime.run(
            "save note",
            principal=Principal(user_id="u1", scopes={"notes.write"}),
            allowed_tools={"save_note"},
            confirmations={"save_note"},
        )
        self.assertEqual(state.status, RunStatus.COMPLETED)
        self.assertEqual(state.tool_results[0].output["saved"], True)
        self.assertEqual(state.tool_results[0].output["idempotent_replay"], False)

    async def test_side_effect_idempotency_replays_same_request(self) -> None:
        reset_demo_state()
        key = f"test-key-{uuid4().hex}"

        first = await save_note({"title": "A", "content": "B", "idempotency_key": key})
        second = await save_note({"title": "A", "content": "B", "idempotency_key": key})

        self.assertEqual(first["note_id"], second["note_id"])
        self.assertEqual(first["idempotent_replay"], False)
        self.assertEqual(second["idempotent_replay"], True)

    async def test_side_effect_idempotency_conflict_fails(self) -> None:
        reset_demo_state()
        key = f"test-key-{uuid4().hex}"

        await save_note({"title": "A", "content": "B", "idempotency_key": key})

        with self.assertRaises(ValidationRuntimeError):
            await save_note({"title": "A", "content": "changed", "idempotency_key": key})

    async def test_sqlite_store_persists_final_state(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteRunStore(Path(tmpdir) / "runs.sqlite3")
            model = ScriptedFakeModel(
                [
                    ToolCallRequest("search_documents", {"query": "runtime", "top_k": 1}),
                    FinalAnswer("persisted"),
                ]
            )
            runtime = AgentRuntime(model=model, store=store)
            state = await runtime.run(
                "find runtime docs",
                principal=Principal(user_id="u1", scopes={"documents.read"}),
                allowed_tools={"search_documents"},
            )

            loaded = await store.get(state.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, RunStatus.COMPLETED)
        self.assertEqual(loaded.final_answer, "persisted")
        self.assertEqual(loaded.trace_id, state.trace_id)
        self.assertEqual(loaded.tool_results[0].output["items"][0]["id"], "doc_1")


if __name__ == "__main__":
    unittest.main()
