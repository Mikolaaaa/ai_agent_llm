from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import time
from typing import Any, Protocol


class EventSink(Protocol):
    def emit(self, event: str, *, trace_id: str, run_id: str, data: dict[str, Any] | None = None) -> None:
        ...


@dataclass(slots=True)
class InMemoryEventSink:
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: str, *, trace_id: str, run_id: str, data: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "timestamp": time(),
                "event": event,
                "trace_id": trace_id,
                "run_id": run_id,
                "data": data or {},
            }
        )


class JsonStdoutEventSink:
    def emit(self, event: str, *, trace_id: str, run_id: str, data: dict[str, Any] | None = None) -> None:
        print(
            json.dumps(
                {
                    "timestamp": time(),
                    "event": event,
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "data": data or {},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

