from __future__ import annotations

from collections import Counter

from agent_runtime.core.state import AgentRunState, Message, MessageRole, Principal, RunLimits, RunStatus
from agent_runtime.core.errors import (
    LimitRuntimeError,
    ModelProtocolRuntimeError,
    RuntimeErrorInfo,
    map_exception,
)
from agent_runtime.observability.events import EventSink, InMemoryEventSink
from agent_runtime.engine.executor import ToolExecutor
from agent_runtime.model.fake import FinalAnswer, ModelAdapter, ToolCallRequest
from agent_runtime.engine.permissions import PermissionService, RunPolicy
from agent_runtime.tools.registry import ToolRegistry
from agent_runtime.storage.memory import InMemoryRunStore, RunStore
from agent_runtime.tools.builtin import build_default_registry


class AgentRuntime:
    def __init__(
        self,
        *,
        model: ModelAdapter,
        registry: ToolRegistry | None = None,
        store: RunStore | None = None,
        events: EventSink | None = None,
        permissions: PermissionService | None = None,
        executor: ToolExecutor | None = None,
    ) -> None:
        self.model = model
        self.registry = registry or build_default_registry()
        self.store = store or InMemoryRunStore()
        self.events = events or InMemoryEventSink()
        self.permissions = permissions or PermissionService()
        self.executor = executor or ToolExecutor()

    async def run(
        self,
        user_message: str,
        *,
        principal: Principal,
        allowed_tools: set[str],
        limits: RunLimits | None = None,
        session_id: str | None = None,
        context: dict | None = None,
        confirmations: set[str] | None = None,
    ) -> AgentRunState:
        state = AgentRunState.create(
            user_message,
            session_id=session_id,
            limits=limits,
            context=context,
            metadata={"allowed_tools": sorted(allowed_tools), "principal": principal.to_dict()},
        )
        policy = RunPolicy(
            allowed_tools=allowed_tools,
            principal=principal,
            confirmations=confirmations or set(),
        )
        await self.store.create(state)
        self._event(state, "run_created")

        try:
            state.transition(RunStatus.RUNNING)
            self._event(state, "run_started")
            await self.store.save(state)

            while True:
                self._assert_iteration_allowed(state)
                state.iterations += 1
                self._event(state, "model_decision_started", {"iteration": state.iterations})
                available_tools = self.registry.public_schemas(allowed_tools)
                decision = await self.model.decide(state=state, available_tools=available_tools)

                if isinstance(decision, FinalAnswer):
                    state.complete(decision.content)
                    self._event(state, "run_completed", {"summary": state.summary().to_dict()})
                    await self.store.save(state)
                    return state

                if not isinstance(decision, ToolCallRequest):
                    raise ModelProtocolRuntimeError("Model returned an unsupported decision object.")

                self._assert_tool_limits(state, decision.tool_name)
                tool = self.registry.get(decision.tool_name)
                arguments = tool.validate_input(decision.arguments)
                self.permissions.assert_allowed(tool=tool, arguments=arguments, policy=policy)

                state.transition(RunStatus.WAITING_TOOL)
                call = state.add_tool_call(tool.name, arguments)
                self._event(
                    state,
                    "tool_call_started",
                    {"tool_name": tool.name, "call_id": call.id, "attempts": call.attempts},
                )
                await self.store.save(state)

                result = await self.executor.execute(
                    tool=tool,
                    call=call,
                    timeout_seconds=state.limits.tool_timeout_seconds,
                    max_output_chars=state.limits.max_tool_output_chars,
                    max_retries=state.limits.max_retries,
                )
                state.add_tool_result(result)
                state.messages.append(
                    Message(
                        role=MessageRole.TOOL,
                        content=str(result.output if result.ok else result.error.to_dict()),
                        metadata={"tool_name": tool.name, "call_id": call.id, "ok": result.ok},
                    )
                )
                self._event(
                    state,
                    "tool_call_finished",
                    {
                        "tool_name": tool.name,
                        "call_id": call.id,
                        "ok": result.ok,
                        "attempts": call.attempts,
                        "error": result.error.to_dict() if result.error else None,
                    },
                )
                state.transition(RunStatus.RUNNING)
                await self.store.save(state)

                if not result.ok:
                    state.fail(result.error or RuntimeErrorInfo(
                        type=map_exception(RuntimeError("unknown")).type,
                        code="tool_failed",
                        message="Tool failed without error details.",
                    ))
                    self._event(state, "run_failed", {"summary": state.summary().to_dict()})
                    await self.store.save(state)
                    return state
        except BaseException as exc:
            error = map_exception(exc)
            if state.status not in {RunStatus.COMPLETED, RunStatus.FAILED}:
                state.fail(error)
            self._event(state, "run_failed", {"error": error.to_dict(), "summary": state.summary().to_dict()})
            await self.store.save(state)
            return state

    def _assert_iteration_allowed(self, state: AgentRunState) -> None:
        if state.iterations >= state.limits.max_iterations:
            raise LimitRuntimeError(
                "Agent exceeded max_iterations.",
                details={
                    "max_iterations": state.limits.max_iterations,
                    "iterations": state.iterations,
                },
            )

    def _assert_tool_limits(self, state: AgentRunState, tool_name: str) -> None:
        if len(state.tool_calls) >= state.limits.max_tool_calls:
            raise LimitRuntimeError(
                "Agent exceeded max_tool_calls.",
                details={"max_tool_calls": state.limits.max_tool_calls},
            )
        counts = Counter(call.name for call in state.tool_calls)
        if counts[tool_name] >= state.limits.max_calls_per_tool:
            raise LimitRuntimeError(
                f"Agent exceeded max_calls_per_tool for '{tool_name}'.",
                details={"tool_name": tool_name, "max_calls_per_tool": state.limits.max_calls_per_tool},
            )

    def _event(self, state: AgentRunState, event: str, data: dict | None = None) -> None:
        self.events.emit(event, trace_id=state.trace_id, run_id=state.id, data=data)
