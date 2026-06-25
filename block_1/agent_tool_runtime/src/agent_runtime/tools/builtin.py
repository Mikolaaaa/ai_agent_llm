from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from agent_runtime.core.errors import DependencyRuntimeError, ValidationRuntimeError
from agent_runtime.tools.registry import ToolDefinition, ToolRegistry


DOCUMENTS = {
    "doc_1": {
        "id": "doc_1",
        "title": "Agent runtime basics",
        "content": "Runtime controls state, tool validation, permissions, limits and final status.",
    },
    "doc_2": {
        "id": "doc_2",
        "title": "Tool contracts",
        "content": "Tool schema is both model-facing description and backend execution contract.",
    },
    "doc_3": {
        "id": "doc_3",
        "title": "Safe tool execution",
        "content": "Runtime must handle allowlists, validation, timeouts, retries and audit logs.",
    },
}

NOTES: dict[str, dict[str, Any]] = {}


async def search_documents(args: dict[str, Any]) -> dict[str, Any]:
    query = args["query"].lower()
    top_k = args.get("top_k", 3)
    items = [
        {"id": doc["id"], "title": doc["title"], "snippet": doc["content"][:120]}
        for doc in DOCUMENTS.values()
        if query in doc["title"].lower() or query in doc["content"].lower()
    ][:top_k]
    return {"items": items}


async def get_document(args: dict[str, Any]) -> dict[str, Any]:
    document_id = args["document_id"]
    if document_id not in DOCUMENTS:
        raise ValidationRuntimeError(
            f"Document '{document_id}' does not exist.",
            details={"document_id": document_id},
        )
    return DOCUMENTS[document_id]


async def calculator(args: dict[str, Any]) -> dict[str, Any]:
    expression = args["expression"]
    allowed = set("0123456789+-*/(). ")
    if any(char not in allowed for char in expression):
        raise ValidationRuntimeError("Calculator expression contains forbidden characters.")
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307 - restricted educational demo
    except Exception as exc:
        raise ValidationRuntimeError("Calculator expression is invalid.") from exc
    return {"result": float(result)}


async def save_note(args: dict[str, Any]) -> dict[str, Any]:
    note_id = f"note_{uuid4().hex[:8]}"
    NOTES[note_id] = {"id": note_id, "title": args["title"], "content": args["content"]}
    return {"note_id": note_id, "saved": True}


async def flaky_status(args: dict[str, Any]) -> dict[str, Any]:
    attempts = args.setdefault("_attempts", 0)
    args["_attempts"] = attempts + 1
    if attempts == 0:
        raise DependencyRuntimeError("Temporary dependency failure.")
    return {"status": "ok"}


async def slow_tool(args: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(args["sleep_seconds"])
    return {"slept_seconds": args["sleep_seconds"]}


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search_documents",
            description="Search in a small in-memory document collection.",
            required_scopes={"documents.read"},
            retryable=False,
            handler=search_documents,
            input_schema={
                "type": "object",
                "required": ["query"],
                "additionalProperties": False,
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 200},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
                },
            },
            output_schema={
                "type": "object",
                "required": ["items"],
                "additionalProperties": False,
                "properties": {
                    "items": {
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
        ToolDefinition(
            name="get_document",
            description="Read one document by ID.",
            required_scopes={"documents.read"},
            resource_arg="document_id",
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
        ToolDefinition(
            name="calculator",
            description="Evaluate a simple arithmetic expression.",
            required_scopes={"calculator.use"},
            retryable=False,
            handler=calculator,
            input_schema={
                "type": "object",
                "required": ["expression"],
                "additionalProperties": False,
                "properties": {"expression": {"type": "string", "minLength": 1, "maxLength": 120}},
            },
            output_schema={
                "type": "object",
                "required": ["result"],
                "additionalProperties": False,
                "properties": {"result": {"type": "number"}},
            },
        )
    )
    registry.register(
        ToolDefinition(
            name="save_note",
            description="Save a note. This is a side-effect tool and requires confirmation.",
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
        ToolDefinition(
            name="flaky_status",
            description="Demo retryable dependency tool.",
            required_scopes={"status.read"},
            retryable=True,
            handler=flaky_status,
            input_schema={"type": "object", "additionalProperties": True, "properties": {}},
            output_schema={
                "type": "object",
                "required": ["status"],
                "additionalProperties": False,
                "properties": {"status": {"type": "string"}},
            },
        )
    )
    registry.register(
        ToolDefinition(
            name="slow_tool",
            description="Demo timeout tool.",
            required_scopes={"debug.use"},
            retryable=True,
            timeout_seconds=0.01,
            handler=slow_tool,
            input_schema={
                "type": "object",
                "required": ["sleep_seconds"],
                "additionalProperties": False,
                "properties": {"sleep_seconds": {"type": "number", "minimum": 0}},
            },
            output_schema={
                "type": "object",
                "required": ["slept_seconds"],
                "additionalProperties": False,
                "properties": {"slept_seconds": {"type": "number"}},
            },
        )
    )
    return registry
