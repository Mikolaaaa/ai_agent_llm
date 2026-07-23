from __future__ import annotations

from statistics import mean
from typing import Any
from uuid import uuid4

from mcp_tool_server.data import DOCUMENTS, NOTES, USER_CONTEXTS
from mcp_tool_server.errors import MCPDependencyError, MCPValidationError


async def search_documents(args: dict[str, Any]) -> dict[str, Any]:
    query = args["query"].lower()
    limit = args.get("limit", 3)
    items = [
        {"id": doc["id"], "title": doc["title"], "snippet": doc["content"][:140]}
        for doc in DOCUMENTS.values()
        if query in doc["title"].lower() or query in doc["content"].lower()
    ][:limit]
    return {"documents": items}


async def get_document(args: dict[str, Any]) -> dict[str, Any]:
    document_id = args["document_id"]
    try:
        return DOCUMENTS[document_id]
    except KeyError as exc:
        raise MCPValidationError(
            f"Document '{document_id}' does not exist.",
            details={"document_id": document_id},
        ) from exc


async def save_note(args: dict[str, Any]) -> dict[str, Any]:
    note_id = f"note_{uuid4().hex[:8]}"
    NOTES[note_id] = {
        "id": note_id,
        "title": args["title"],
        "content": args["content"],
        "source_document_id": args.get("source_document_id"),
    }
    return {"note_id": note_id, "saved": True}


async def calculate_metric(args: dict[str, Any]) -> dict[str, Any]:
    values = args["values"]
    metric = args["metric"]
    if metric == "count":
        result = len(values)
    elif metric == "sum":
        result = sum(values)
    elif metric == "avg":
        result = mean(values)
    else:
        raise MCPValidationError(
            f"Unsupported metric '{metric}'.",
            details={"metric": metric},
        )
    return {"metric": metric, "value": float(result)}


async def get_user_context(args: dict[str, Any]) -> dict[str, Any]:
    user_id = args["user_id"]
    try:
        return USER_CONTEXTS[user_id]
    except KeyError as exc:
        raise MCPValidationError(
            f"User context for '{user_id}' does not exist.",
            details={"user_id": user_id},
        ) from exc


async def unstable_dependency(args: dict[str, Any]) -> dict[str, Any]:
    raise MCPDependencyError("Simulated temporary upstream failure.")
