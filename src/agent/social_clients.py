from __future__ import annotations


class XClient:
    """Placeholder untuk tahap 2: posting otomatis ke X API resmi."""

    def post(self, content: str) -> None:
        raise NotImplementedError("Integrasi X API belum diaktifkan.")


class InstagramClient:
    """Placeholder untuk tahap 3: posting via Instagram Graph API."""

    def post_feed(self, caption: str, media_url: str) -> None:
        raise NotImplementedError("Integrasi Instagram Graph API belum diaktifkan.")

