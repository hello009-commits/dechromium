from __future__ import annotations

from pydantic import BaseModel


class CreateRequest(BaseModel):
    name: str = "default"
    platform: str | None = None
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    languages: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None
    identity: dict | None = None
    hardware: dict | None = None
    webgl: dict | None = None
    noise: dict | None = None
    network: dict | None = None
    fonts: dict | None = None
    notes: str = ""


class UpdateRequest(BaseModel):
    name: str | None = None
    notes: str | None = None
    identity: dict | None = None
    hardware: dict | None = None
    webgl: dict | None = None
    noise: dict | None = None
    network: dict | None = None
    fonts: dict | None = None


class StartRequest(BaseModel):
    headless: bool = True
    extra_args: list[str] | None = None
    timeout: float = 15.0


class CookieImportRequest(BaseModel):
    path: str | None = None
    cookies: list[dict] | None = None
