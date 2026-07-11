from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib import parse, request

from .config import Settings


class XClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.url = "https://api.x.com/2/tweets"

    def post_text(self, text: str) -> str:
        if not self.settings.x_ready:
            raise RuntimeError("X belum aktif. Isi X_ENABLED dan token X di Railway Variables.")
        payload = json.dumps({"text": text[:280]}).encode("utf-8")
        headers = {
            "Authorization": self._authorization_header("POST", self.url),
            "Content-Type": "application/json",
        }
        http_request = request.Request(self.url, data=payload, headers=headers, method="POST")
        with request.urlopen(http_request, timeout=35) as response:
            data = json.loads(response.read().decode("utf-8"))
        tweet_id = data.get("data", {}).get("id")
        return f"https://x.com/parisbolaku/status/{tweet_id}" if tweet_id else "Post terkirim ke X."

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
