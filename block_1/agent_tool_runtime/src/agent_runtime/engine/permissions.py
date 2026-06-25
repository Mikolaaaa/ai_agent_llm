from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_runtime.core.state import Principal
from agent_runtime.core.errors import PermissionRuntimeError
from agent_runtime.tools.registry import ToolDefinition


@dataclass(slots=True)
class RunPolicy:
    allowed_tools: set[str]
    principal: Principal
    require_confirmation_for_side_effects: bool = True
    confirmations: set[str] = field(default_factory=set)


class PermissionService:
    def assert_allowed(
        self,
        *,
        tool: ToolDefinition,
        arguments: dict[str, Any],
        policy: RunPolicy,
    ) -> None:
        if tool.name not in policy.allowed_tools:
            raise PermissionRuntimeError(
                f"Tool '{tool.name}' is not allowed for this run.",
                details={"tool_name": tool.name, "allowed_tools": sorted(policy.allowed_tools)},
            )

        missing_scopes = sorted(tool.required_scopes - policy.principal.scopes)
        if missing_scopes:
            raise PermissionRuntimeError(
                f"Principal does not have required scopes for tool '{tool.name}'.",
                details={"tool_name": tool.name, "missing_scopes": missing_scopes},
            )

        if tool.resource_arg:
            resource_id = arguments.get(tool.resource_arg)
            if resource_id and resource_id not in policy.principal.owned_document_ids:
                raise PermissionRuntimeError(
                    f"Principal cannot access resource '{resource_id}'.",
                    details={"resource_arg": tool.resource_arg, "resource_id": resource_id},
                )

        if (
            tool.side_effect
            and policy.require_confirmation_for_side_effects
            and tool.name not in policy.confirmations
        ):
            raise PermissionRuntimeError(
                f"Tool '{tool.name}' requires explicit confirmation.",
                details={"tool_name": tool.name, "confirmation_required": True},
            )
