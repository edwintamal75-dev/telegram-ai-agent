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
    photo_url: str | None
    destination: str


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
                    created_at TEXT NOT NULL,
                    photo_url TEXT,
                    destination TEXT NOT NULL DEFAULT 'telegram'
                )
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(posts)").fetchall()
            }
            if "photo_url" not in columns:
                connection.execute("ALTER TABLE posts ADD COLUMN photo_url TEXT")
            if "destination" not in columns:
                connection.execute("ALTER TABLE posts ADD COLUMN destination TEXT NOT NULL DEFAULT 'telegram'")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_post_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_key TEXT NOT NULL UNIQUE,
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
        photo_url: str | None = None,
        destination: str = "telegram",
    ) -> int:
        status = "scheduled" if scheduled_at else "draft"
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO posts (content, status, scheduled_at, created_by, created_at, photo_url, destination)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content,
                    status,
                    scheduled_at.isoformat() if scheduled_at else None,
                    created_by,
                    datetime.utcnow().isoformat(),
                    photo_url,
                    destination,
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

    def auto_post_was_sent(self, slot_key: str) -> bool:
        with self.connect() as connection:
            row = connection.execute("SELECT 1 FROM auto_post_log WHERE slot_key = ?", (slot_key,)).fetchone()
        return row is not None

    def mark_auto_post_sent(self, slot_key: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO auto_post_log (slot_key, created_at) VALUES (?, ?)",
                (slot_key, datetime.utcnow().isoformat()),
            )

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
            photo_url=row["photo_url"],
            destination=str(row["destination"]),
        )
