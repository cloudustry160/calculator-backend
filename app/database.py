from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS calculation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expression TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_calculation_history_created_at
ON calculation_history (created_at DESC);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00",
        "Z",
    )


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def health_check(self) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 AS healthy").fetchone()
        return row is not None and row["healthy"] == 1

    def create_history(self, expression: str, result: Decimal) -> dict:
        created_at = utc_now_iso()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO calculation_history (expression, result, created_at)
                VALUES (?, ?, ?)
                """,
                (expression, str(result), created_at),
            )
            record_id = cursor.lastrowid

        return {
            "id": record_id,
            "expression": expression,
            "result": result,
            "created_at": created_at,
        }

    def list_history(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, expression, result, created_at
                FROM calculation_history
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

        return [
            {
                "id": row["id"],
                "expression": row["expression"],
                "result": Decimal(row["result"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def delete_history(self, record_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM calculation_history WHERE id = ?",
                (record_id,),
            )
            return cursor.rowcount > 0

    def clear_history(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM calculation_history")
