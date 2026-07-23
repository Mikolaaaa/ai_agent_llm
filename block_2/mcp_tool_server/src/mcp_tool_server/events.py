from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass(slots=True)
class Event:
    name: str
    trace_id: str
    data: dict[str, Any]
    created_at: float = field(default_factory=time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "data": self.data,
            "created_at": self.created_at,
        }


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, name: str, *, trace_id: str, data: dict[str, Any] | None = None) -> None:
        self.events.append(Event(name=name, trace_id=trace_id, data=data or {}))

    def list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]

