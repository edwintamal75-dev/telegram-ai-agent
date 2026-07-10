from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class PostDraft:
    id: int
    content: str
    status: str
    scheduled_at: str | None
    created_by: int | None
    created_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    scheduled_at TEXT,
                    created_by INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_post(
        self,
        content: str,
        *,
        created_by: int | None = None,
        scheduled_at: datetime | None = None,
    ) -> int:
        status = "scheduled" if scheduled_at else "draft"
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO posts (content, status, scheduled_at, created_by, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    content,
                    status,
                    scheduled_at.isoformat() if scheduled_at else None,
                    created_by,
                    datetime.utcnow().isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def list_pending(self) -> list[PostDraft]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM posts
                WHERE status IN ('draft', 'scheduled')
                ORDER BY id DESC
                LIMIT 20
                """
            ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def get_post(self, post_id: int) -> PostDraft | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return self._row_to_post(row) if row else None

    def due_posts(self, now: datetime) -> list[PostDraft]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM posts
                WHERE status = 'scheduled'
                  AND scheduled_at IS NOT NULL
                  AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                """,
                (now.isoformat(),),
            ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def mark_posted(self, post_id: int) -> None:
        self._set_status(post_id, "posted")

    def cancel(self, post_id: int) -> None:
        self._set_status(post_id, "cancelled")

    def _set_status(self, post_id: int, status: str) -> None:
        with self.connect() as connection:
            connection.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))

    @staticmethod
    def _row_to_post(row: sqlite3.Row) -> PostDraft:
        return PostDraft(
            id=int(row["id"]),
            content=str(row["content"]),
            status=str(row["status"]),
            scheduled_at=row["scheduled_at"],
            created_by=row["created_by"],
            created_at=str(row["created_at"]),
        )

