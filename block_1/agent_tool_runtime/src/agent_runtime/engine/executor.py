from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from agent_runtime.core.state import ToolCall, ToolResult
from agent_runtime.core.errors import (
    AgentRuntimeError,
    RuntimeErrorInfo,
    TimeoutRuntimeError,
    map_exception,
)
from agent_runtime.tools.registry import ToolDefinition
from agent_runtime.core.validation import validate_output_size


class ToolExecutor:
    async def execute(
        self,
        *,
        tool: ToolDefinition,
        call: ToolCall,
        timeout_seconds: float,
        max_output_chars: int,
        max_retries: int,
    ) -> ToolResult:
        attempts = 0
        last_error: RuntimeErrorInfo | None = None
        max_attempts = max_retries + 1 if tool.retryable else 1

        while attempts < max_attempts:
            attempts += 1
            call.attempts = attempts
            started = perf_counter()
            try:
                raw_output = await asyncio.wait_for(
                    tool.handler(call.arguments),
                    timeout=tool.timeout_seconds or timeout_seconds,
                )
                if not isinstance(raw_output, dict):
                    raise AgentRuntimeError("Tool handler must return a dict.")
                validate_output_size(raw_output, max_output_chars)
                output = tool.validate_output(raw_output)
                return ToolResult(
                    call_id=call.id,
                    tool_name=tool.name,
                    output=output,
                    ok=True,
                    latency_ms=(perf_counter() - started) * 1000,
                )
            except asyncio.TimeoutError as exc:
                last_error = TimeoutRuntimeError(
                    f"Tool '{tool.name}' exceeded timeout.",
                    details={"tool_name": tool.name, "timeout_seconds": timeout_seconds},
                ).to_info()
                if not last_error.retryable or attempts >= max_attempts:
                    break
            except BaseException as exc:
                last_error = map_exception(exc)
                if not last_error.retryable or attempts >= max_attempts:
                    break

        return ToolResult(
            call_id=call.id,
            tool_name=tool.name,
            output=None,
            ok=False,
            error=last_error,
        )
