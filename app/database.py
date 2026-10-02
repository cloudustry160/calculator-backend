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
    kind TEXT NOT NULL DEFAULT 'calculation',
    is_favorite INTEGER NOT NULL DEFAULT 0,
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
            self._ensure_column(
                connection,
                "kind",
                "TEXT NOT NULL DEFAULT 'calculation'",
            )
            self._ensure_column(
                connection,
                "is_favorite",
                "INTEGER NOT NULL DEFAULT 0",
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                ix_calculation_history_favorite_created_at
                ON calculation_history (is_favorite DESC, created_at DESC)
                """
            )

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        column_name: str,
        declaration: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(calculation_history)"
            ).fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE calculation_history "
                f"ADD COLUMN {column_name} {declaration}"
            )

    def health_check(self) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 AS healthy").fetchone()
        return row is not None and row["healthy"] == 1

    def create_history(
        self,
        expression: str,
        result: str | Decimal,
        kind: str = "calculation",
    ) -> dict:
        created_at = utc_now_iso()
        result_text = str(result)

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO calculation_history (
                    expression,
                    result,
                    kind,
                    is_favorite,
                    created_at
                )
                VALUES (?, ?, ?, 0, ?)
                """,
                (expression, result_text, kind, created_at),
            )
            record_id = cursor.lastrowid

        return self._row_to_record(
            {
                "id": record_id,
                "expression": expression,
                "result": result_text,
                "kind": kind,
                "is_favorite": 0,
                "created_at": created_at,
            }
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row | dict) -> dict:
        return {
            "id": row["id"],
            "expression": row["expression"],
            "result": row["result"],
            "kind": row["kind"],
            "is_favorite": bool(row["is_favorite"]),
            "created_at": row["created_at"],
        }

    def list_history(
        self,
        page: int = 1,
        page_size: int = 10,
        query: str = "",
        favorite_only: bool = False,
    ) -> dict:
        normalized_query = query.strip()
        conditions: list[str] = []
        parameters: list[object] = []

        if normalized_query:
            escaped_query = (
                normalized_query.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            conditions.append(
                "(expression LIKE ? ESCAPE '\\' OR result LIKE ? ESCAPE '\\')"
            )
            parameters.extend((f"%{escaped_query}%", f"%{escaped_query}%"))

        if favorite_only:
            conditions.append("is_favorite = 1")

        where_clause = ""
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)}"

        offset = (page - 1) * page_size

        with self._connect() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM calculation_history "
                f"{where_clause}",
                parameters,
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    expression,
                    result,
                    kind,
                    is_favorite,
                    created_at
                FROM calculation_history
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, offset],
            ).fetchall()

        total = int(total_row["total"])
        return {
            "records": [self._row_to_record(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    def get_history(self, record_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    expression,
                    result,
                    kind,
                    is_favorite,
                    created_at
                FROM calculation_history
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

        return self._row_to_record(row) if row is not None else None

    def set_favorite(self, record_id: int, favorite: bool) -> dict | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE calculation_history
                SET is_favorite = ?
                WHERE id = ?
                """,
                (1 if favorite else 0, record_id),
            )
            if cursor.rowcount == 0:
                return None

            row = connection.execute(
                """
                SELECT
                    id,
                    expression,
                    result,
                    kind,
                    is_favorite,
                    created_at
                FROM calculation_history
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

        return self._row_to_record(row)

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
