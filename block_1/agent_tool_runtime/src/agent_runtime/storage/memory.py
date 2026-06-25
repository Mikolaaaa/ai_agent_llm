from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from agent_runtime.core.state import AgentRunState


class RunStore(Protocol):
    async def create(self, state: AgentRunState) -> None: ...
    async def get(self, run_id: str) -> AgentRunState | None: ...
    async def save(self, state: AgentRunState) -> None: ...


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRunState] = {}

    async def create(self, state: AgentRunState) -> None:
        self._runs[state.id] = deepcopy(state)

    async def get(self, run_id: str) -> AgentRunState | None:
        state = self._runs.get(run_id)
        return deepcopy(state) if state else None

    async def save(self, state: AgentRunState) -> None:
        self._runs[state.id] = deepcopy(state)
