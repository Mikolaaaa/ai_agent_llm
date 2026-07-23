from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from mcp_tool_server.core.errors import MCPContractError, MCPValidationError
from mcp_tool_server.core.validation import JSONSchema, assert_valid_schema, validate_payload


PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {PROTOCOL_VERSION}
ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ToolContract:
    name: str
    title: str
    description: str
    input_schema: JSONSchema
    output_schema: JSONSchema
    required_scopes: set[str]
    handler: ToolHandler
    timeout_seconds: float = 1.0
    retryable: bool = False
    side_effect: bool = False
    version: str = "1.0.0"
    annotations: dict[str, Any] = field(default_factory=dict)

    def validate_contract(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise MCPContractError("Tool name must be a non-empty string.")
        if " " in self.name or "," in self.name:
            raise MCPContractError(
                "Tool name must not contain spaces or commas.",
                details={"tool_name": self.name},
            )
        try:
            assert_valid_schema(self.input_schema, label=f"{self.name}.inputSchema")
            assert_valid_schema(self.output_schema, label=f"{self.name}.outputSchema")
        except MCPValidationError as exc:
            raise MCPContractError(
                "Tool contract schema is invalid.",
                details={"tool_name": self.name, "schema_error": exc.to_info().to_dict()},
            ) from exc
        if self.timeout_seconds <= 0:
            raise MCPContractError(
                "Tool timeout must be positive.",
                details={"tool_name": self.name, "timeout_seconds": self.timeout_seconds},
            )

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_payload(payload, self.input_schema, label=f"{self.name}.input")

    def validate_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_payload(payload, self.output_schema, label=f"{self.name}.output")

    def to_mcp_tool(self) -> dict[str, Any]:
        self.validate_contract()
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "annotations": {
                "readOnlyHint": not self.side_effect,
                "destructiveHint": self.side_effect,
                **self.annotations,
            },
            "x-runtime": {
                "version": self.version,
                "required_scopes": sorted(self.required_scopes),
                "retryable": self.retryable,
                "side_effect": self.side_effect,
                "timeout_seconds": self.timeout_seconds,
            },
        }


@dataclass(slots=True)
class ServerContext:
    trace_id: str = "trace_direct"
    allowed_tools: set[str] = field(default_factory=set)
    scopes: set[str] = field(default_factory=set)
    confirmations: set[str] = field(default_factory=set)

    @classmethod
    def allow_all(cls, *, trace_id: str = "trace_direct") -> ServerContext:
        return cls(trace_id=trace_id, allowed_tools={"*"}, scopes={"*"}, confirmations={"*"})


@dataclass(slots=True)
class MCPToolCallResult:
    content: list[dict[str, Any]]
    structured_content: dict[str, Any] | None
    is_error: bool = False

    def to_mcp_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {"content": self.content, "isError": self.is_error}
        if self.structured_content is not None:
            result["structuredContent"] = self.structured_content
        return result
