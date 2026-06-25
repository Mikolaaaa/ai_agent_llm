from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from agent_runtime.core.errors import ToolNotFoundRuntimeError, ValidationRuntimeError
from agent_runtime.core.validation import JSONSchema, validate_payload


ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: JSONSchema
    output_schema: JSONSchema
    required_scopes: set[str]
    handler: ToolHandler
    timeout_seconds: float | None = None
    retryable: bool = False
    side_effect: bool = False
    resource_arg: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_payload(payload, self.input_schema, label=f"{self.name}.input")

    def validate_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_payload(payload, self.output_schema, label=f"{self.name}.output")

    def public_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_scopes": sorted(self.required_scopes),
            "timeout_seconds": self.timeout_seconds,
            "retryable": self.retryable,
            "side_effect": self.side_effect,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValidationRuntimeError(
                f"Tool '{definition.name}' is already registered.",
                details={"tool_name": definition.name},
            )
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundRuntimeError(
                f"Tool '{name}' is not registered.",
                details={"tool_name": name},
            ) from exc

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def public_schemas(self, allowed_tools: set[str] | None = None) -> list[dict[str, Any]]:
        tools = self.list()
        if allowed_tools is not None:
            tools = [tool for tool in tools if tool.name in allowed_tools]
        return [tool.public_schema() for tool in tools]
