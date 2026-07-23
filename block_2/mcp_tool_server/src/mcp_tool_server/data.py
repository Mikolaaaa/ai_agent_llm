from __future__ import annotations

from typing import Any


DOCUMENTS = {
    "doc_mcp_1": {
        "id": "doc_mcp_1",
        "title": "MCP boundary",
        "content": "MCP separates agent runtime orchestration from external tool execution.",
    },
    "doc_mcp_2": {
        "id": "doc_mcp_2",
        "title": "Tool contracts",
        "content": "A tool contract includes name, description, input schema, output schema and errors.",
    },
    "doc_mcp_3": {
        "id": "doc_mcp_3",
        "title": "Safe external tools",
        "content": "External tools need validation, permissions, timeouts, retries and trace logs.",
    },
}

USER_CONTEXTS = {
    "user_1": {
        "user_id": "user_1",
        "role": "student",
        "active_block": "block_2_mcp",
        "preferences": {
            "language": "ru",
            "explanation_style": "direct_and_practical",
        },
    },
    "demo_user": {
        "user_id": "demo_user",
        "role": "demo",
        "active_block": "block_2_mcp",
        "preferences": {
            "language": "ru",
            "explanation_style": "short_check_in_demo",
        },
    },
}

NOTES: dict[str, dict[str, Any]] = {}


def reset_demo_state() -> None:
    NOTES.clear()
