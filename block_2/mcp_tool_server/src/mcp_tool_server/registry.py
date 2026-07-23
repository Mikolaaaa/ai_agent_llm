from __future__ import annotations

from mcp_tool_server.contracts import ToolContract
from mcp_tool_server.errors import MCPContractError, MCPToolNotFoundError
from mcp_tool_server.tools import (
    calculate_metric,
    get_document,
    get_user_context,
    save_note,
    search_documents,
    unstable_dependency,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolContract] = {}

    def register(self, tool: ToolContract) -> None:
        tool.validate_contract()
        if tool.name in self._tools:
            raise MCPContractError(
                f"Tool '{tool.name}' is already registered.",
                details={"tool_name": tool.name},
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolContract:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise MCPToolNotFoundError(
                f"Tool '{name}' is not registered.",
                details={"tool_name": name},
            ) from exc

    def list(self) -> list[ToolContract]:
        return list(self._tools.values())

    def list_mcp_tools(self) -> list[dict]:
        return [tool.to_mcp_tool() for tool in self.list()]


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolContract(
            name="search_documents",
            title="Search Documents",
            description="Search demo documents by text query. Returns ids, titles and snippets.",
            required_scopes={"documents.read"},
            retryable=False,
            handler=search_documents,
            input_schema={
                "type": "object",
                "required": ["query"],
                "additionalProperties": False,
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 200},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 5},
                },
            },
            output_schema={
                "type": "object",
                "required": ["documents"],
                "additionalProperties": False,
                "properties": {
                    "documents": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "required": ["id", "title", "snippet"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "snippet": {"type": "string"},
                            },
                        },
                    }
                },
            },
        )
    )
    registry.register(
        ToolContract(
            name="get_document",
            title="Get Document",
            description="Read one demo document by id.",
            required_scopes={"documents.read"},
            retryable=False,
            handler=get_document,
            input_schema={
                "type": "object",
                "required": ["document_id"],
                "additionalProperties": False,
                "properties": {"document_id": {"type": "string", "minLength": 1}},
            },
            output_schema={
                "type": "object",
                "required": ["id", "title", "content"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        )
    )
    registry.register(
        ToolContract(
            name="save_note",
            title="Save Note",
            description="Save a note in memory. This tool has side effects and requires confirmation.",
            required_scopes={"notes.write"},
            retryable=False,
            side_effect=True,
            handler=save_note,
            input_schema={
                "type": "object",
                "required": ["title", "content"],
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 100},
                    "content": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "source_document_id": {"type": "string", "minLength": 1},
                },
            },
            output_schema={
                "type": "object",
                "required": ["note_id", "saved"],
                "additionalProperties": False,
                "properties": {
                    "note_id": {"type": "string"},
                    "saved": {"type": "boolean"},
                },
            },
        )
    )
    registry.register(
        ToolContract(
            name="calculate_metric",
            title="Calculate Metric",
            description="Calculate count, sum or average for numeric values.",
            required_scopes={"metrics.calculate"},
            retryable=False,
            handler=calculate_metric,
            input_schema={
                "type": "object",
                "required": ["values", "metric"],
                "additionalProperties": False,
                "properties": {
                    "values": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 100,
                        "items": {"type": "number"},
                    },
                    "metric": {"type": "string", "enum": ["count", "sum", "avg"]},
                },
            },
            output_schema={
                "type": "object",
                "required": ["metric", "value"],
                "additionalProperties": False,
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "number"},
                },
            },
        )
    )
    registry.register(
        ToolContract(
            name="get_user_context",
            title="Get User Context",
            description="Read safe demo user context for agent personalization.",
            required_scopes={"user_context.read"},
            retryable=False,
            handler=get_user_context,
            input_schema={
                "type": "object",
                "required": ["user_id"],
                "additionalProperties": False,
                "properties": {"user_id": {"type": "string", "minLength": 1}},
            },
            output_schema={
                "type": "object",
                "required": ["user_id", "role", "active_block", "preferences"],
                "additionalProperties": False,
                "properties": {
                    "user_id": {"type": "string"},
                    "role": {"type": "string"},
                    "active_block": {"type": "string"},
                    "preferences": {
                        "type": "object",
                        "required": ["language", "explanation_style"],
                        "additionalProperties": False,
                        "properties": {
                            "language": {"type": "string"},
                            "explanation_style": {"type": "string"},
                        },
                    },
                },
            },
        )
    )
    registry.register(
        ToolContract(
            name="unstable_dependency",
            title="Unstable Dependency",
            description="Demo tool that always returns a retryable upstream error.",
            required_scopes={"debug.use"},
            retryable=True,
            handler=unstable_dependency,
            input_schema={"type": "object", "additionalProperties": False, "properties": {}},
            output_schema={
                "type": "object",
                "required": ["status"],
                "additionalProperties": False,
                "properties": {"status": {"type": "string"}},
            },
        )
    )
    return registry


def build_incompatible_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolContract(
            name="broken_tool",
            title="Broken Tool",
            description="Invalid contract demo.",
            required_scopes=set(),
            handler=search_documents,
            input_schema={
                "type": "object",
                "required": ["missing_from_properties"],
                "properties": {},
            },
            output_schema={"type": "object", "properties": {}},
        )
    )
    return registry
