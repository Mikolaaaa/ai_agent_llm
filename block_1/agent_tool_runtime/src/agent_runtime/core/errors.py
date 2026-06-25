from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ErrorType(StrEnum):
    VALIDATION = "validation_error"
    RUNTIME = "runtime_error"
    PERMISSION = "permission_error"
    TIMEOUT = "timeout_error"
    LIMIT = "limit_error"
    TOOL_NOT_FOUND = "tool_not_found"
    MODEL_PROTOCOL = "model_protocol_error"


@dataclass(slots=True)
class RuntimeErrorInfo:
    type: ErrorType
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data


class AgentRuntimeError(Exception):
    error_type: ErrorType = ErrorType.RUNTIME
    code: str = "runtime_error"
    retryable: bool = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_info(self) -> RuntimeErrorInfo:
        return RuntimeErrorInfo(
            type=self.error_type,
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.details or None,
        )


class ValidationRuntimeError(AgentRuntimeError):
    error_type = ErrorType.VALIDATION
    code = "invalid_payload"
    retryable = False


class PermissionRuntimeError(AgentRuntimeError):
    error_type = ErrorType.PERMISSION
    code = "permission_denied"
    retryable = False


class TimeoutRuntimeError(AgentRuntimeError):
    error_type = ErrorType.TIMEOUT
    code = "tool_timeout"
    retryable = True


class LimitRuntimeError(AgentRuntimeError):
    error_type = ErrorType.LIMIT
    code = "limit_exceeded"
    retryable = False


class ToolNotFoundRuntimeError(AgentRuntimeError):
    error_type = ErrorType.TOOL_NOT_FOUND
    code = "tool_not_found"
    retryable = False


class ModelProtocolRuntimeError(AgentRuntimeError):
    error_type = ErrorType.MODEL_PROTOCOL
    code = "invalid_model_decision"
    retryable = False


class DependencyRuntimeError(AgentRuntimeError):
    error_type = ErrorType.RUNTIME
    code = "dependency_error"
    retryable = True


def map_exception(exc: BaseException) -> RuntimeErrorInfo:
    if isinstance(exc, AgentRuntimeError):
        return exc.to_info()
    return RuntimeErrorInfo(
        type=ErrorType.RUNTIME,
        code="unhandled_exception",
        message="Tool execution failed with an unexpected runtime error.",
        retryable=False,
        details={"exception_class": exc.__class__.__name__},
    )

