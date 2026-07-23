from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class MCPErrorType(StrEnum):
    VALIDATION = "validation_error"
    PERMISSION = "permission_error"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION = "tool_execution_error"
    PROTOCOL = "protocol_error"
    TIMEOUT = "timeout_error"
    CONTRACT = "contract_error"


@dataclass(slots=True)
class MCPErrorInfo:
    type: MCPErrorType
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data


class MCPServerError(Exception):
    error_type: MCPErrorType = MCPErrorType.TOOL_EXECUTION
    code: str = "tool_execution_error"
    retryable: bool = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_info(self) -> MCPErrorInfo:
        return MCPErrorInfo(
            type=self.error_type,
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.details or None,
        )


class MCPValidationError(MCPServerError):
    error_type = MCPErrorType.VALIDATION
    code = "invalid_payload"
    retryable = False


class MCPPermissionError(MCPServerError):
    error_type = MCPErrorType.PERMISSION
    code = "permission_denied"
    retryable = False


class MCPToolNotFoundError(MCPServerError):
    error_type = MCPErrorType.TOOL_NOT_FOUND
    code = "tool_not_found"
    retryable = False


class MCPToolExecutionError(MCPServerError):
    error_type = MCPErrorType.TOOL_EXECUTION
    code = "tool_execution_error"
    retryable = False


class MCPDependencyError(MCPServerError):
    error_type = MCPErrorType.TOOL_EXECUTION
    code = "dependency_error"
    retryable = True


class MCPTimeoutError(MCPServerError):
    error_type = MCPErrorType.TIMEOUT
    code = "tool_timeout"
    retryable = True


class MCPProtocolError(MCPServerError):
    error_type = MCPErrorType.PROTOCOL
    code = "protocol_error"
    retryable = False


class MCPContractError(MCPServerError):
    error_type = MCPErrorType.CONTRACT
    code = "invalid_contract"
    retryable = False


def map_exception(exc: BaseException) -> MCPErrorInfo:
    if isinstance(exc, MCPServerError):
        return exc.to_info()
    return MCPErrorInfo(
        type=MCPErrorType.TOOL_EXECUTION,
        code="unhandled_exception",
        message="MCP tool execution failed with an unexpected error.",
        retryable=False,
        details={"exception_class": exc.__class__.__name__},
    )
