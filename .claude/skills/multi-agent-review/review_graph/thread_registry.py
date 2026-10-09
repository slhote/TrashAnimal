from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

SQLITE_BUSY_TIMEOUT_SECONDS = 10

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS review_threads (
    thread_id TEXT PRIMARY KEY,
    scope_label TEXT NOT NULL,
    pid INTEGER,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    running_since REAL
)
"""


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    scope_label: str
    pid: int | None
    created_at: float
    updated_at: float
    running_since: float | None


class ThreadRegistry:
    """Index of review threads. Holds only liveness metadata; review state lives in the checkpoint."""

    def __init__(
        self,
        database_path: str | Path,
        clock: Callable[[], float] = time.time,
        current_pid: Callable[[], int] = os.getpid,
    ):
        self._database_path = str(database_path)
        self._clock = clock
        self._current_pid = current_pid
        with self._transaction() as connection:
            connection.execute(CREATE_TABLE)

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self._database_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def begin(self, thread_id: str, scope_label: str, fresh: bool) -> None:
        """Mark the thread as being worked on by this process. A fresh run replaces any earlier row."""
        now, pid = self._clock(), self._current_pid()
        with self._transaction() as connection:
            exists = connection.execute("SELECT 1 FROM review_threads WHERE thread_id = ?", (thread_id,)).fetchone()
            if fresh or not exists:
                connection.execute(
                    "INSERT OR REPLACE INTO review_threads "
                    "(thread_id, scope_label, pid, created_at, updated_at, running_since) VALUES (?, ?, ?, ?, ?, ?)",
                    (thread_id, scope_label, pid, now, now, now),
                )
            else:
                connection.execute(
                    "UPDATE review_threads SET pid = ?, updated_at = ?, running_since = ? WHERE thread_id = ?",
                    (pid, now, now, thread_id),
                )

    def mark_idle(self, thread_id: str) -> None:
        with self._transaction() as connection:
            connection.execute(
                "UPDATE review_threads SET running_since = NULL, updated_at = ? WHERE thread_id = ?",
                (self._clock(), thread_id),
            )

    def remove(self, thread_id: str) -> None:
        with self._transaction() as connection:
            connection.execute("DELETE FROM review_threads WHERE thread_id = ?", (thread_id,))

    def get(self, thread_id: str) -> ThreadRecord | None:
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT thread_id, scope_label, pid, created_at, updated_at, running_since "
                "FROM review_threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return ThreadRecord(*row) if row else None

    def list_all(self) -> list[ThreadRecord]:
        with self._transaction() as connection:
            rows = connection.execute(
                "SELECT thread_id, scope_label, pid, created_at, updated_at, running_since "
                "FROM review_threads ORDER BY updated_at DESC"
            ).fetchall()
        return [ThreadRecord(*row) for row in rows]
