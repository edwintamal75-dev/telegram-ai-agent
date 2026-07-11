from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError

from .config import Settings
from .database import Database
from .llm import AIWriter


class PostScheduler:
    def __init__(self, settings: Settings, database: Database, ai_writer: AIWriter, send_post) -> None:
        self.settings = settings
        self.database = database
        self.ai_writer = ai_writer
        self.send_post = send_post
        self.timezone = _timezone(settings.default_timezone)

    async def run_forever(self) -> None:
        while True:
            await self.publish_due_posts()
            await asyncio.sleep(30)

    async def publish_due_posts(self) -> None:
        now = datetime.now(self.timezone)
        for post in self.database.due_posts(now):
            await self.send_post(post.content, post.photo_url, post.destination)
            self.database.mark_posted(post.id)
            await asyncio.sleep(1)
        await self.publish_auto_daily(now)

    async def publish_auto_daily(self, now: datetime) -> None:
        if not self.settings.auto_daily_enabled:
            return
        current_time = now.strftime("%H:%M")
        if current_time not in self.settings.auto_daily_times:
            return
        slot_key = f"{now.date().isoformat()}-{current_time}"
        if self.database.auto_post_was_sent(slot_key):
            return
        slot_name = _slot_name(current_time)
        content = self.ai_writer.daily_post(slot_name)
        await self.send_post(content, None)
        self.database.mark_auto_post_sent(slot_key)


def _timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Bangkok":
            return timezone(timedelta(hours=7), name="Asia/Bangkok")
        return timezone.utc


def _slot_name(time_text: str) -> str:
    if time_text < "12:00":
        return "pagi - agenda bola dan topik pembuka hari ini"
    if time_text < "18:00":
        return "sore - transfer, berita klub, atau opini singkat"
    return "malam - big match, prediksi, atau pertanyaan diskusi"
