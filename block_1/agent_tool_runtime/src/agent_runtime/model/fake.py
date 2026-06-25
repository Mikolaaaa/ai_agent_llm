from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent_runtime.core.state import AgentRunState


@dataclass(slots=True)
class ToolCallRequest:
    tool_name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class FinalAnswer:
    content: str


ModelDecision = ToolCallRequest | FinalAnswer


class ModelAdapter(Protocol):
    async def decide(
        self,
        *,
        state: AgentRunState,
        available_tools: list[dict[str, Any]],
    ) -> ModelDecision:
        ...


class ScriptedFakeModel:
    """Deterministic fake model for tests and demos."""

    def __init__(self, decisions: list[ModelDecision]) -> None:
        self._decisions = list(decisions)
        self.calls = 0

    async def decide(
        self,
        *,
        state: AgentRunState,
        available_tools: list[dict[str, Any]],
    ) -> ModelDecision:
        self.calls += 1
        if not self._decisions:
            return FinalAnswer("No scripted decision left.")
        return self._decisions.pop(0)


class KeywordFakeModel:
    """Tiny deterministic model used by CLI/API demos.

    It is intentionally not an LLM. It simulates model decisions so the backend
    runtime can be tested without network calls or provider credentials.
    """

    async def decide(
        self,
        *,
        state: AgentRunState,
        available_tools: list[dict[str, Any]],
    ) -> ModelDecision:
        user_text = state.messages[0].content.lower()
        successful_results = [result for result in state.tool_results if result.ok]
        failed_results = [result for result in state.tool_results if not result.ok]

        if failed_results:
            error = failed_results[-1].error
            code = error.code if error else "unknown_error"
            return FinalAnswer(f"Не удалось выполнить запрос: {code}.")

        if successful_results:
            last = successful_results[-1]
            if last.tool_name == "calculator":
                return FinalAnswer(f"Результат вычисления: {last.output['result']}.")
            if last.tool_name == "search_documents":
                titles = ", ".join(item["title"] for item in last.output["items"])
                return FinalAnswer(f"Нашёл документы: {titles}.")
            if last.tool_name == "get_document":
                return FinalAnswer(f"Документ: {last.output['title']}\n{last.output['content']}")
            if last.tool_name == "save_note":
                return FinalAnswer(f"Заметка сохранена: {last.output['note_id']}.")

        if "loop" in user_text:
            return ToolCallRequest(tool_name="search_documents", arguments={"query": "loop", "top_k": 1})
        if "invalid" in user_text:
            return ToolCallRequest(tool_name="search_documents", arguments={"query": "", "top_k": 100})
        if "forbidden" in user_text:
            return ToolCallRequest(tool_name="save_note", arguments={"title": "x", "content": "y"})
        if "calculate" in user_text or "calc" in user_text:
            return ToolCallRequest(tool_name="calculator", arguments={"expression": "2 + 2 * 3"})
        if "document" in user_text and "get" in user_text:
            return ToolCallRequest(tool_name="get_document", arguments={"document_id": "doc_1"})
        if "save" in user_text or "note" in user_text:
            return ToolCallRequest(
                tool_name="save_note",
                arguments={"title": "Runtime note", "content": state.messages[0].content},
            )
        query = state.messages[0].content
        if "agent runtime" in user_text:
            query = "runtime"
        elif "tool" in user_text:
            query = "tool"
        return ToolCallRequest(tool_name="search_documents", arguments={"query": query, "top_k": 3})
