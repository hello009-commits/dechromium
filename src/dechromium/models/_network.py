from __future__ import annotations

from pydantic import BaseModel, Field

from ._enums import WebRTCPolicy


class Network(BaseModel):
    proxy: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    webrtc_policy: WebRTCPolicy = WebRTCPolicy.DISABLE_NON_PROXIED_UDP
    timezone: str = "America/New_York"
    locale: str = "en-US"
    languages: list[str] = Field(default_factory=lambda: ["en-US", "en"])
    latitude: float | None = None
    longitude: float | None = None
