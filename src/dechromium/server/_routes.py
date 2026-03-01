from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException

from dechromium import __version__
from dechromium._exceptions import BrowserError, BrowserTimeoutError, ProfileNotFoundError

from ._schemas import CookieImportRequest, CreateRequest, StartRequest, UpdateRequest

if TYPE_CHECKING:
    from dechromium._client import Dechromium

_DEFAULT_START = StartRequest()


def create_app(dc: Dechromium) -> FastAPI:
    app = FastAPI(title="dechromium", version=__version__)

    @app.post("/profiles")
    def create_profile(req: CreateRequest):
        kwargs = req.model_dump(exclude_none=True)
        name = kwargs.pop("name", "default")
        profile = dc.create(name, **kwargs)
        return profile.model_dump()

    @app.get("/profiles")
    def list_profiles():
        return [p.model_dump() for p in dc.list()]

    @app.get("/profiles/{profile_id}")
    def get_profile(profile_id: str):
        try:
            return dc.get(profile_id).model_dump()
        except ProfileNotFoundError as exc:
            raise HTTPException(404, "Profile not found") from exc

    @app.put("/profiles/{profile_id}")
    def update_profile(profile_id: str, req: UpdateRequest):
        kwargs = req.model_dump(exclude_none=True)
        try:
            profile = dc.update(profile_id, **kwargs)
        except ProfileNotFoundError as exc:
            raise HTTPException(404, "Profile not found") from exc
        return profile.model_dump()

    @app.delete("/profiles/{profile_id}")
    def delete_profile(profile_id: str):
        if not dc.delete(profile_id):
            raise HTTPException(404, "Profile not found")
        return {"deleted": True}

    @app.post("/profiles/{profile_id}/start")
    def start_browser(profile_id: str, req: StartRequest = _DEFAULT_START):
        try:
            info = dc.start(
                profile_id,
                headless=req.headless,
                extra_args=req.extra_args,
                timeout=req.timeout,
            )
        except ProfileNotFoundError as exc:
            raise HTTPException(404, "Profile not found") from exc
        except BrowserTimeoutError as exc:
            raise HTTPException(504, str(exc)) from exc
        except BrowserError as exc:
            raise HTTPException(500, str(exc)) from exc
        return {
            "profile_id": info.profile_id,
            "pid": info.pid,
            "debug_port": info.debug_port,
            "ws_endpoint": info.ws_endpoint,
            "cdp_url": info.cdp_url,
        }

    @app.post("/profiles/{profile_id}/stop")
    def stop_browser(profile_id: str):
        return {"stopped": dc.stop(profile_id)}

    @app.get("/profiles/{profile_id}/status")
    def browser_status(profile_id: str):
        return dc.status(profile_id)

    @app.get("/running")
    def list_running():
        return [
            {
                "profile_id": i.profile_id,
                "pid": i.pid,
                "debug_port": i.debug_port,
                "ws_endpoint": i.ws_endpoint,
                "cdp_url": i.cdp_url,
            }
            for i in dc.running()
        ]

    @app.post("/profiles/{profile_id}/cookies/import")
    def do_import_cookies(profile_id: str, req: CookieImportRequest):
        try:
            dc.get(profile_id)
        except ProfileNotFoundError as exc:
            raise HTTPException(404, "Profile not found") from exc
        if req.cookies:
            count = dc.import_cookies(profile_id, req.cookies)
        elif req.path:
            count = dc.import_cookies(profile_id, req.path)
        else:
            raise HTTPException(400, "Provide 'path' or 'cookies'")
        return {"imported": count}

    @app.get("/profiles/{profile_id}/cookies/export")
    def do_export_cookies(profile_id: str):
        try:
            dc.get(profile_id)
        except ProfileNotFoundError as exc:
            raise HTTPException(404, "Profile not found") from exc
        return dc.export_cookies(profile_id)

    @app.post("/stop-all")
    def stop_all():
        dc.stop_all()
        return {"stopped": True}

    @app.get("/check")
    def check_profiles():
        return dc.check_profiles()

    @app.post("/upgrade-profiles")
    def upgrade_profiles():
        upgraded = dc.upgrade_profiles(progress=False)
        return {"upgraded": upgraded, "count": len(upgraded)}

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "profiles": len(dc.list()),
            "running": len(dc.running()),
        }

    return app
