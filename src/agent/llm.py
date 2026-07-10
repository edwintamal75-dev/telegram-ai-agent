from __future__ import annotations

import json
from urllib import request

from .config import Settings


class AIWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def caption(self, topic: str) -> str:
        prompt = (
            "Buat caption media sosial berbahasa Indonesia yang jelas, natural, "
            "tidak berlebihan, dan cocok untuk Telegram. Sertakan call to action ringan.\n\n"
            f"Topik: {topic}"
        )
        return self._generate(prompt)

    def reply(self, message: str) -> str:
        prompt = (
            "Kamu adalah admin grup Telegram yang ramah, singkat, dan membantu. "
            "Jawab dalam bahasa Indonesia. Jika pertanyaan tidak jelas, minta klarifikasi.\n\n"
            f"Pesan member: {message}"
        )
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:
        if self.settings.dry_run or not self.settings.openai_ready:
            return f"[DRY RUN] Contoh respons AI untuk: {prompt[:180]}"

        payload = json.dumps(
            {
                "model": self.settings.openai_model,
                "input": prompt,
            }
        ).encode("utf-8")
        http_request = request.Request(
            "https://api.openai.com/v1/responses",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(http_request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return _extract_output_text(data).strip()


def _extract_output_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts) or "AI belum mengembalikan teks."
