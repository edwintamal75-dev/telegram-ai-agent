from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib import parse, request
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError

from .config import Settings
from .database import Database
from .llm import AIWriter
from .scheduler import PostScheduler


class TelegramAgentBot:
    def __init__(self, settings: Settings, database: Database, ai_writer: AIWriter) -> None:
        self.settings = settings
        self.database = database
        self.ai_writer = ai_writer
        self.timezone = _timezone(settings.default_timezone)
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.scheduler = PostScheduler(settings, database, self.send_channel_post)
        self.offset = 0

    async def send_channel_post(self, content: str) -> None:
        if self.settings.dry_run:
            print(f"[DRY RUN] Posting ke channel {self.settings.telegram_channel_id}: {content}")
            return
        if not self.settings.telegram_channel_id:
            raise RuntimeError("TELEGRAM_CHANNEL_ID belum diisi.")
        await self._send_message(self.settings.telegram_channel_id, content)

    def run(self) -> None:
        if self.settings.dry_run:
            print("DRY_RUN aktif. Ubah DRY_RUN=false di .env untuk menjalankan bot sungguhan.")
            return
        if not self.settings.telegram_ready:
            raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi.")
        asyncio.run(self._run())

    async def _run(self) -> None:
        print(f"{self.settings.app_name} berjalan. Channel target: {self.settings.telegram_channel_id}")
        await asyncio.gather(self._poll_updates(), self.scheduler.run_forever())

    async def _poll_updates(self) -> None:
        while True:
            try:
                updates = await self._get_updates()
                for update in updates:
                    self.offset = max(self.offset, int(update["update_id"]) + 1)
                    await self._handle_update(update)
            except Exception as exc:
                print(f"Polling error: {exc}")
                await asyncio.sleep(5)

    async def _handle_update(self, update: dict) -> None:
        message = update.get("message") or update.get("channel_post")
        if not message or "text" not in message:
            return
        text = message["text"].strip()
        chat_id = message["chat"]["id"]
        user_id = message.get("from", {}).get("id")

        if text.startswith("/start"):
            await self._send_message(
                chat_id,
                f"{self.settings.app_name} aktif.\n"
                "Gunakan /caption, /post, /pending, /approve, /schedule, atau /cancel.",
            )
        elif text.startswith("/caption"):
            topic = self._command_args(text)
            if not topic:
                await self._send_message(chat_id, "Tulis topiknya. Contoh: /caption big match malam ini")
                return
            await self._send_message(chat_id, self.ai_writer.caption(topic))
        elif text.startswith("/post"):
            if not await self._is_admin(chat_id, user_id):
                return
            content = self._command_args(text)
            if not content:
                await self._send_message(chat_id, "Tulis isi posting. Contoh: /post Halo Matchday AI aktif.")
                return
            post_id = self.database.create_post(content, created_by=user_id)
            await self._send_message(chat_id, f"Draft #{post_id} dibuat. Kirim /approve {post_id} untuk posting.")
        elif text.startswith("/pending"):
            if not await self._is_admin(chat_id, user_id):
                return
            await self._pending(chat_id)
        elif text.startswith("/approve"):
            if not await self._is_admin(chat_id, user_id):
                return
            await self._approve(chat_id, self._first_int(text))
        elif text.startswith("/schedule"):
            if not await self._is_admin(chat_id, user_id):
                return
            await self._schedule(chat_id, user_id, self._command_args(text))
        elif text.startswith("/cancel"):
            if not await self._is_admin(chat_id, user_id):
                return
            post_id = self._first_int(text)
            if post_id is None:
                await self._send_message(chat_id, "Masukkan ID draft. Contoh: /cancel 3")
                return
            self.database.cancel(post_id)
            await self._send_message(chat_id, f"Draft #{post_id} dibatalkan.")
        elif self.settings.auto_reply_enabled and len(text) >= 4:
            await self._send_message(chat_id, self.ai_writer.reply(text))

    async def _pending(self, chat_id: int) -> None:
        posts = self.database.list_pending()
        if not posts:
            await self._send_message(chat_id, "Belum ada draft atau jadwal pending.")
            return
        lines = []
        for post in posts:
            preview = post.content.replace("\n", " ")[:80]
            schedule = f" | {post.scheduled_at}" if post.scheduled_at else ""
            lines.append(f"#{post.id} [{post.status}{schedule}] {preview}")
        await self._send_message(chat_id, "\n".join(lines))

    async def _approve(self, chat_id: int, post_id: int | None) -> None:
        if post_id is None:
            await self._send_message(chat_id, "Masukkan ID draft. Contoh: /approve 3")
            return
        post = self.database.get_post(post_id)
        if post is None or post.status not in {"draft", "scheduled"}:
            await self._send_message(chat_id, "Draft tidak ditemukan atau sudah tidak pending.")
            return
        await self.send_channel_post(post.content)
        self.database.mark_posted(post.id)
        await self._send_message(chat_id, f"Draft #{post.id} sudah diposting.")

    async def _schedule(self, chat_id: int, user_id: int | None, raw: str) -> None:
        try:
            date_text, time_text, content = raw.split(" ", 2)
            scheduled_at = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M").replace(
                tzinfo=self.timezone
            )
        except ValueError:
            await self._send_message(
                chat_id,
                "Format jadwal: /schedule YYYY-MM-DD HH:MM isi konten\n"
                "Contoh: /schedule 2026-07-10 19:30 Update pertandingan malam ini.",
            )
            return
        post_id = self.database.create_post(content, created_by=user_id, scheduled_at=scheduled_at)
        await self._send_message(chat_id, f"Posting #{post_id} dijadwalkan pada {scheduled_at.isoformat()}.")

    async def _is_admin(self, chat_id: int, user_id: int | None) -> bool:
        if not self.settings.telegram_allowed_admin_ids:
            return True
        if user_id in self.settings.telegram_allowed_admin_ids:
            return True
        await self._send_message(chat_id, "Perintah ini hanya untuk admin yang diizinkan.")
        return False

    async def _get_updates(self) -> list[dict]:
        params = {"timeout": 25, "offset": self.offset, "allowed_updates": json.dumps(["message"])}
        data = await asyncio.to_thread(self._telegram_request, "getUpdates", params)
        return data.get("result", [])

    async def _send_message(self, chat_id: int | str, text: str) -> None:
        params = {"chat_id": chat_id, "text": text}
        await asyncio.to_thread(self._telegram_request, "sendMessage", params)

    def _telegram_request(self, method: str, params: dict) -> dict:
        encoded = parse.urlencode(params).encode("utf-8")
        http_request = request.Request(f"{self.base_url}/{method}", data=encoded, method="POST")
        with request.urlopen(http_request, timeout=35) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not data.get("ok"):
            raise RuntimeError(data)
        return data

    @staticmethod
    def _command_args(text: str) -> str:
        parts = text.split(" ", 1)
        return parts[1].strip() if len(parts) > 1 else ""

    @staticmethod
    def _first_int(text: str) -> int | None:
        args = TelegramAgentBot._command_args(text)
        if not args:
            return None
        try:
            return int(args.split()[0])
        except ValueError:
            return None


def _timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Bangkok":
            return timezone(timedelta(hours=7), name="Asia/Bangkok")
        return timezone.utc
