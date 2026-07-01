from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent_runtime.core.state import AgentRunState


class SQLiteRunStore:
    """Durable RunStore implementation backed by local SQLite.

    The runtime stores the whole state JSON plus indexed fields useful for
    listing/debugging. This keeps the adapter small and makes the persistence
    boundary explicit for the block-1 prototype.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._init_schema()

    async def create(self, state: AgentRunState) -> None:
        self._upsert(state)

    async def get(self, run_id: str) -> AgentRunState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentRunState.from_dict(json.loads(row[0]))

    async def save(self, state: AgentRunState) -> None:
        self._upsert(state)

    def _init_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )

    def _upsert(self, state: AgentRunState) -> None:
        state_json = json.dumps(state.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (run_id, trace_id, session_id, status, updated_at, state_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    trace_id = excluded.trace_id,
                    session_id = excluded.session_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    state_json = excluded.state_json
                """,
                (
                    state.id,
                    state.trace_id,
                    state.session_id,
                    state.status.value,
                    state.updated_at,
                    state_json,
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

