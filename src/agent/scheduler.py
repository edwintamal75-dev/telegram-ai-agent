from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError

from .config import Settings
from .database import Database


class PostScheduler:
    def __init__(self, settings: Settings, database: Database, send_post) -> None:
        self.settings = settings
        self.database = database
        self.send_post = send_post
        self.timezone = _timezone(settings.default_timezone)

    async def run_forever(self) -> None:
        while True:
            await self.publish_due_posts()
            await asyncio.sleep(30)

    async def publish_due_posts(self) -> None:
        now = datetime.now(self.timezone)
        for post in self.database.due_posts(now):
            await self.send_post(post.content)
            self.database.mark_posted(post.id)
            await asyncio.sleep(1)


def _timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Bangkok":
            return timezone(timedelta(hours=7), name="Asia/Bangkok")
        return timezone.utc
