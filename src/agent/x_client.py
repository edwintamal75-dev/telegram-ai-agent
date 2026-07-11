from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from urllib.error import HTTPError
from urllib import parse, request

from .config import Settings


class XClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.create_post_url = "https://api.x.com/2/tweets"
        self.media_upload_url = "https://upload.twitter.com/1.1/media/upload.json"

    def post_text(self, text: str, image_url: str | None = None) -> str:
        if not self.settings.x_ready:
            raise RuntimeError("X belum aktif. Isi X_ENABLED dan token X di Railway Variables.")
        payload_data: dict = {"text": text[:280]}
        if image_url:
            media_id = self.upload_image_from_url(image_url)
            payload_data["media"] = {"media_ids": [media_id]}
        payload = json.dumps(payload_data).encode("utf-8")
        headers = {
            "Authorization": self._authorization_header("POST", self.create_post_url),
            "Content-Type": "application/json",
        }
        http_request = request.Request(self.create_post_url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"X API error {exc.code}: {error_body}") from exc
        tweet_id = data.get("data", {}).get("id")
        return f"https://x.com/parisbolaku/status/{tweet_id}" if tweet_id else "Post terkirim ke X."

    def upload_image_from_url(self, image_url: str) -> str:
        image_bytes, content_type = self._download_image(image_url)
        boundary = f"----matchdayai{uuid.uuid4().hex}"
        body = _multipart_body(boundary, image_bytes, content_type)
        headers = {
            "Authorization": self._authorization_header("POST", self.media_upload_url),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        http_request = request.Request(self.media_upload_url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"X media upload error {exc.code}: {error_body}") from exc
        media_id = data.get("media_id_string")
        if not media_id:
            raise RuntimeError(f"X media upload tidak mengembalikan media_id: {data}")
        return str(media_id)

    @staticmethod
    def _download_image(image_url: str) -> tuple[bytes, str]:
        http_request = request.Request(image_url, headers={"User-Agent": "MatchdayAI/1.0"})
        with request.urlopen(http_request, timeout=35) as response:
            content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
            image_bytes = response.read(5 * 1024 * 1024 + 1)
        if len(image_bytes) > 5 * 1024 * 1024:
            raise RuntimeError("Ukuran gambar terlalu besar untuk upload sederhana. Pakai gambar di bawah 5 MB.")
        if not content_type.startswith("image/"):
            raise RuntimeError(f"URL tidak terlihat sebagai gambar. Content-Type: {content_type}")
        return image_bytes, content_type

    def _authorization_header(self, method: str, url: str) -> str:
        oauth_params = {
            "oauth_consumer_key": self.settings.x_api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.settings.x_access_token,
            "oauth_version": "1.0",
        }
        signature = self._signature(method, url, oauth_params)
        oauth_params["oauth_signature"] = signature
        header_params = ", ".join(
            f'{key}="{parse.quote(value, safe="")}"' for key, value in sorted(oauth_params.items())
        )
        return f"OAuth {header_params}"

    def _signature(self, method: str, url: str, oauth_params: dict[str, str]) -> str:
        parameter_string = "&".join(
            f"{parse.quote(key, safe='')}={parse.quote(value, safe='')}"
            for key, value in sorted(oauth_params.items())
        )
        base_string = "&".join(
            (
                method.upper(),
                parse.quote(url, safe=""),
                parse.quote(parameter_string, safe=""),
            )
        )
        signing_key = (
            f"{parse.quote(self.settings.x_api_key_secret, safe='')}"
            f"&{parse.quote(self.settings.x_access_token_secret, safe='')}"
        )
        digest = hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
        return base64.b64encode(digest).decode("utf-8")


def _multipart_body(boundary: str, image_bytes: bytes, content_type: str) -> bytes:
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="media"; filename="image.jpg"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + image_bytes + tail
