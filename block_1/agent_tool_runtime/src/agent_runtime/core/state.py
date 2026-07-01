from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from time import time
from typing import Any
from uuid import uuid4

from agent_runtime.core.errors import RuntimeErrorInfo


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ToolCallStatus(StrEnum):
    REQUESTED = "requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class Message:
    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class RunLimits:
    max_iterations: int = 6
    max_tool_calls: int = 8
    max_calls_per_tool: int = 4
    tool_timeout_seconds: float = 1.0
    max_tool_output_chars: int = 5_000
    max_retries: int = 1

    def validate(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.max_tool_calls < 0:
            raise ValueError("max_tool_calls must be >= 0")
        if self.max_calls_per_tool < 0:
            raise ValueError("max_calls_per_tool must be >= 0")
        if self.tool_timeout_seconds <= 0:
            raise ValueError("tool_timeout_seconds must be > 0")
        if self.max_tool_output_chars < 1:
            raise ValueError("max_tool_output_chars must be >= 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunLimits:
        return cls(**data)


@dataclass(slots=True)
class Principal:
    user_id: str
    scopes: set[str] = field(default_factory=set)
    owned_document_ids: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "scopes": sorted(self.scopes),
            "owned_document_ids": sorted(self.owned_document_ids),
        }


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.REQUESTED
    attempts: int = 0
    error: RuntimeErrorInfo | None = None
    created_at: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "attempts": self.attempts,
            "error": self.error.to_dict() if self.error else None,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        return cls(
            id=data["id"],
            name=data["name"],
            arguments=data["arguments"],
            status=ToolCallStatus(data["status"]),
            attempts=data.get("attempts", 0),
            error=RuntimeErrorInfo.from_dict(data["error"]) if data.get("error") else None,
            created_at=data["created_at"],
        )


@dataclass(slots=True)
class ToolResult:
    call_id: str
    tool_name: str
    output: dict[str, Any] | None
    ok: bool
    error: RuntimeErrorInfo | None = None
    latency_ms: float | None = None
    created_at: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "output": self.output,
            "ok": self.ok,
            "error": self.error.to_dict() if self.error else None,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolResult:
        return cls(
            call_id=data["call_id"],
            tool_name=data["tool_name"],
            output=data.get("output"),
            ok=bool(data["ok"]),
            error=RuntimeErrorInfo.from_dict(data["error"]) if data.get("error") else None,
            latency_ms=data.get("latency_ms"),
            created_at=data["created_at"],
        )


@dataclass(slots=True)
class RunSummary:
    status: RunStatus
    iterations: int
    tool_calls: int
    errors: int
    terminal_reason: str
    tools_called: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "iterations": self.iterations,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "terminal_reason": self.terminal_reason,
            "tools_called": self.tools_called,
        }


@dataclass(slots=True)
class AgentRunState:
    id: str
    trace_id: str
    session_id: str
    status: RunStatus
    messages: list[Message]
    context: dict[str, Any]
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]
    artifacts: dict[str, Any]
    limits: RunLimits
    metadata: dict[str, Any]
    iterations: int = 0
    final_answer: str | None = None
    error: RuntimeErrorInfo | None = None
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)

    @classmethod
    def create(
        cls,
        user_message: str,
        *,
        session_id: str | None = None,
        trace_id: str | None = None,
        limits: RunLimits | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentRunState:
        run_limits = limits or RunLimits()
        run_limits.validate()
        return cls(
            id=f"run_{uuid4().hex[:12]}",
            trace_id=trace_id or f"trace_{uuid4().hex[:12]}",
            session_id=session_id or f"session_{uuid4().hex[:12]}",
            status=RunStatus.CREATED,
            messages=[Message(role=MessageRole.USER, content=user_message)],
            context=context or {},
            tool_calls=[],
            tool_results=[],
            artifacts={},
            limits=run_limits,
            metadata=metadata or {},
        )

    def transition(self, next_status: RunStatus) -> None:
        terminal = {RunStatus.COMPLETED, RunStatus.FAILED}
        allowed = {
            RunStatus.CREATED: {RunStatus.RUNNING, RunStatus.FAILED},
            RunStatus.RUNNING: {
                RunStatus.WAITING_TOOL,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            },
            RunStatus.WAITING_TOOL: {RunStatus.RUNNING, RunStatus.FAILED},
            RunStatus.COMPLETED: set(),
            RunStatus.FAILED: set(),
        }
        if self.status in terminal:
            raise ValueError(f"Cannot transition from terminal status {self.status.value}")
        if next_status not in allowed[self.status]:
            raise ValueError(f"Invalid transition {self.status.value} -> {next_status.value}")
        self.status = next_status
        self.updated_at = time()

    def add_tool_call(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        call = ToolCall(id=f"call_{uuid4().hex[:12]}", name=name, arguments=arguments)
        self.tool_calls.append(call)
        self.updated_at = time()
        return call

    def add_tool_result(self, result: ToolResult) -> None:
        self.tool_results.append(result)
        for call in self.tool_calls:
            if call.id == result.call_id:
                call.status = ToolCallStatus.SUCCEEDED if result.ok else ToolCallStatus.FAILED
                call.error = result.error
                break
        self.updated_at = time()

    def complete(self, answer: str) -> None:
        self.final_answer = answer
        self.messages.append(Message(role=MessageRole.ASSISTANT, content=answer))
        self.transition(RunStatus.COMPLETED)

    def fail(self, error: RuntimeErrorInfo) -> None:
        self.error = error
        self.transition(RunStatus.FAILED)

    def summary(self) -> RunSummary:
        error_count = len([result for result in self.tool_results if not result.ok])
        if self.error:
            error_count += 1
        reason = "completed" if self.status == RunStatus.COMPLETED else "failed"
        if self.error:
            reason = self.error.code
        return RunSummary(
            status=self.status,
            iterations=self.iterations,
            tool_calls=len(self.tool_calls),
            errors=error_count,
            terminal_reason=reason,
            tools_called=[call.name for call in self.tool_calls],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "messages": [message.to_dict() for message in self.messages],
            "context": self.context,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "tool_results": [result.to_dict() for result in self.tool_results],
            "artifacts": self.artifacts,
            "limits": self.limits.to_dict(),
            "metadata": self.metadata,
            "iterations": self.iterations,
            "final_answer": self.final_answer,
            "error": self.error.to_dict() if self.error else None,
            "summary": self.summary().to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRunState:
        return cls(
            id=data["id"],
            trace_id=data["trace_id"],
            session_id=data["session_id"],
            status=RunStatus(data["status"]),
            messages=[Message.from_dict(message) for message in data.get("messages", [])],
            context=data.get("context", {}),
            tool_calls=[ToolCall.from_dict(call) for call in data.get("tool_calls", [])],
            tool_results=[
                ToolResult.from_dict(result) for result in data.get("tool_results", [])
            ],
            artifacts=data.get("artifacts", {}),
            limits=RunLimits.from_dict(data["limits"]),
            metadata=data.get("metadata", {}),
            iterations=data.get("iterations", 0),
            final_answer=data.get("final_answer"),
            error=RuntimeErrorInfo.from_dict(data["error"]) if data.get("error") else None,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
