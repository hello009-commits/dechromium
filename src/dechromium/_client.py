from __future__ import annotations

import contextlib
import logging
import random
from pathlib import Path
from urllib.parse import urlparse

from dechromium._config import Config
from dechromium._fonts import ensure_fonts
from dechromium._installer import BrowserManager
from dechromium.browser import BrowserInfo, BrowserPool
from dechromium.browser._cookies import export_cookies, import_cookies
from dechromium.models import Platform, Profile
from dechromium.profile import DiversityEngine, ProfileManager
from dechromium.profile._launcher import build_launch_args, build_launch_env

logger = logging.getLogger(__name__)

_COUNTRY_LOCALES: dict | None = None

_NAV_PLATFORM = {
    Platform.WINDOWS: "Win32",
    Platform.MACOS: "MacIntel",
    Platform.LINUX: "Linux x86_64",
}

_PLATFORMS: dict[str, dict] = {
    "windows": {
        "identity": {
            "platform": "Win32",
            "ua_platform": "Windows",
            "ua_platform_version": "15.0.0",
            "ua_arch": "x86",
        },
        "webgl": {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": (
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 "
                "(0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)"
            ),
        },
        "fonts": {"font_pack": "windows"},
    },
    "macos": {
        "identity": {
            "platform": "MacIntel",
            "ua_platform": "macOS",
            "ua_platform_version": "14.5.0",
            "ua_arch": "arm",
        },
        "webgl": {
            "vendor": "Google Inc. (Apple)",
            "renderer": "ANGLE (Apple, Apple M1, OpenGL 4.1)",
        },
        "fonts": {"font_pack": "macos"},
    },
    "linux": {
        "identity": {
            "platform": "Linux x86_64",
            "ua_platform": "Linux",
            "ua_platform_version": "",
            "ua_arch": "x86",
        },
        "webgl": {
            "vendor": "Google Inc. (Mesa)",
            "renderer": "ANGLE (Mesa, llvmpipe, OpenGL 4.5)",
        },
        "fonts": {"font_pack": "linux"},
    },
}


class Dechromium:
    def __init__(self, config: Config | None = None, **kwargs):
        self.config = config or Config(**kwargs)
        self._manager = ProfileManager(self.config)
        self._browsers = BrowserManager(self.config.data_dir)

        from dechromium import __version__

        ensure_fonts(self.config.fonts_dir, __version__)

        self._pool = BrowserPool(
            port_start=self.config.debug_port_start,
            port_end=self.config.debug_port_end,
        )

    def create(
        self,
        name: str = "default",
        *,
        platform: Platform | str | None = None,
        proxy: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        languages: list[str] | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        cores: int | None = None,
        memory: float | None = None,
        screen: tuple[int, int] | None = None,
        webgl_vendor: str | None = None,
        webgl_renderer: str | None = None,
        gpu_vendor: str | None = None,
        gpu_model: str | None = None,
        identity: dict | None = None,
        hardware: dict | None = None,
        webgl: dict | None = None,
        noise: dict | None = None,
        network: dict | None = None,
        fonts: dict | None = None,
        notes: str = "",
        auto: bool = True,
        seed: int | None = None,
    ) -> Profile:
        platform_str = platform.value if isinstance(platform, Platform) else platform

        if auto:
            nav_platform = None
            if platform_str:
                nav_platform = {
                    "windows": "Win32",
                    "macos": "MacIntel",
                    "linux": "Linux x86_64",
                }.get(platform_str, platform_str)

            engine = DiversityEngine(seed=seed)
            generated = engine.generate(
                platform=nav_platform,
                gpu_vendor=gpu_vendor,
                gpu_model=gpu_model,
                cores=cores,
                memory=memory,
                screen=screen,
            )

            overrides = _build_overrides(
                proxy=proxy,
                timezone=timezone,
                locale=locale,
                languages=languages,
                latitude=latitude,
                longitude=longitude,
                webgl_vendor=webgl_vendor,
                webgl_renderer=webgl_renderer,
                identity=identity,
                hardware=hardware,
                webgl=webgl,
                noise=noise,
                network=network,
                fonts=fonts,
                notes=notes,
            )

            for section in ("identity", "hardware", "webgl", "noise", "fonts"):
                if section in overrides:
                    generated.setdefault(section, {}).update(overrides[section])
                    del overrides[section]
            overrides.update(generated)
        else:
            overrides = _build_overrides(
                platform=platform_str,
                proxy=proxy,
                timezone=timezone,
                locale=locale,
                languages=languages,
                latitude=latitude,
                longitude=longitude,
                cores=cores,
                memory=memory,
                screen=screen,
                webgl_vendor=webgl_vendor,
                webgl_renderer=webgl_renderer,
                identity=identity,
                hardware=hardware,
                webgl=webgl,
                noise=noise,
                network=network,
                fonts=fonts,
                notes=notes,
            )

        return self._manager.create(name, **overrides)

    def get(self, profile_id: str) -> Profile:
        return self._manager.get(profile_id)

    def list(self) -> list[Profile]:
        return self._manager.list_all()

    def update(
        self,
        profile_id: str,
        *,
        name: str | None = None,
        notes: str | None = None,
        identity: dict | None = None,
        hardware: dict | None = None,
        webgl: dict | None = None,
        noise: dict | None = None,
        network: dict | None = None,
        fonts: dict | None = None,
    ) -> Profile:
        overrides: dict = {}
        if name is not None:
            overrides["name"] = name
        if notes is not None:
            overrides["notes"] = notes
        for key, val in [
            ("identity", identity),
            ("hardware", hardware),
            ("webgl", webgl),
            ("noise", noise),
            ("network", network),
            ("fonts", fonts),
        ]:
            if val is not None:
                overrides[key] = val

        return self._manager.update(profile_id, **overrides)

    def delete(self, profile_id: str) -> bool:
        with contextlib.suppress(Exception):
            self._pool.stop(profile_id)
        return self._manager.delete(profile_id)

    def start(
        self,
        profile_id: str,
        headless: bool = True,
        extra_args: list[str] | None = None,
        timeout: float = 15.0,
    ) -> BrowserInfo:
        profile = self._manager.get(profile_id)
        resolved = _resolve_network(profile, self.config.data_dir)
        args = build_launch_args(resolved, self.config, headless=headless)
        env = build_launch_env(resolved, self.config)
        res = f"{profile.hardware.screen_width}x{profile.hardware.screen_height}x24"
        return self._pool.start(
            profile_id,
            args,
            env,
            headless=headless,
            extra_args=extra_args,
            timeout=timeout,
            screen_resolution=res,
        )

    def stop(self, profile_id: str) -> bool:
        return self._pool.stop(profile_id)

    def stop_all(self):
        self._pool.stop_all()

    def status(self, profile_id: str) -> dict:
        return self._pool.status(profile_id)

    def running(self) -> list[BrowserInfo]:
        return self._pool.list_running()

    def import_cookies(self, profile_id: str, source: str | list[dict]) -> int:
        data_dir = self._manager.data_dir(profile_id)
        if isinstance(source, str):
            return import_cookies(data_dir, Path(source))
        return import_cookies(data_dir, source)

    def export_cookies(self, profile_id: str) -> list[dict]:
        data_dir = self._manager.data_dir(profile_id)
        return export_cookies(data_dir)

    def install_browser(
        self,
        version: str | None = None,
        *,
        force: bool = False,
        progress: bool = True,
    ) -> Path:
        return self._browsers.install(version, force=force, progress=progress)

    def update_browsers(self, *, progress: bool = True) -> list[str]:
        return self._browsers.update(progress=progress)

    def list_browsers(self) -> list[dict]:
        return self._browsers.installed()

    def uninstall_browser(self, version: str) -> bool:
        return self._browsers.uninstall(version)

    def check_profiles(self) -> list[dict]:
        from dechromium import __version__

        results = []
        for profile in self._manager.list_all():
            outdated = profile.library_version != __version__
            results.append(
                {
                    "id": profile.id,
                    "name": profile.name,
                    "library_version": profile.library_version,
                    "current_version": __version__,
                    "outdated": outdated,
                }
            )
        return results

    def upgrade_profiles(self, *, progress: bool = True) -> list[str]:
        from dechromium import __version__

        upgraded = []
        for profile in self._manager.list_all():
            if profile.library_version == __version__:
                continue
            self._manager.update(profile.id, library_version=__version__)
            if progress:
                print(f"  Upgraded {profile.name} ({profile.id})")
            upgraded.append(profile.id)
        return upgraded

    def serve(self, host: str | None = None, port: int | None = None):
        try:
            from dechromium.server import create_app
        except ImportError as exc:
            raise ImportError(
                "Server dependencies not installed. Install with: pip install dechromium[server]"
            ) from exc
        import uvicorn

        app = create_app(self)
        uvicorn.run(
            app,
            host=host or self.config.api_host,
            port=port or self.config.api_port,
        )

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop_all()

    def __repr__(self) -> str:
        n_profiles = len(self._manager.list_all())
        n_running = len(self._pool.list_running())
        return f"Dechromium(profiles={n_profiles}, running={n_running})"


def _build_overrides(
    platform: str | None = None,
    proxy: str | None = None,
    timezone: str | None = None,
    locale: str | None = None,
    languages: list[str] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    cores: int | None = None,
    memory: float | None = None,
    screen: tuple[int, int] | None = None,
    webgl_vendor: str | None = None,
    webgl_renderer: str | None = None,
    identity: dict | None = None,
    hardware: dict | None = None,
    webgl: dict | None = None,
    noise: dict | None = None,
    network: dict | None = None,
    fonts: dict | None = None,
    notes: str = "",
) -> dict:
    result: dict = {}

    if platform and platform in _PLATFORMS:
        preset = _PLATFORMS[platform]
        result["identity"] = dict(preset["identity"])
        result["webgl"] = dict(preset["webgl"])
        result["fonts"] = dict(preset["fonts"])

    if identity:
        result.setdefault("identity", {}).update(identity)
    if hardware:
        result.setdefault("hardware", {}).update(hardware)
    if webgl:
        result.setdefault("webgl", {}).update(webgl)
    if noise:
        result["noise"] = noise
    if network:
        result.setdefault("network", {}).update(network)
    if fonts:
        result.setdefault("fonts", {}).update(fonts)

    if proxy:
        parsed = urlparse(proxy)
        net = result.setdefault("network", {})
        if parsed.username:
            clean_proxy = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            net["proxy"] = clean_proxy
            net["proxy_username"] = parsed.username
            net.setdefault("proxy_password", parsed.password or "")
        else:
            net["proxy"] = proxy

    if timezone:
        result.setdefault("network", {})["timezone"] = timezone
    if locale:
        result.setdefault("network", {})["locale"] = locale
    if languages:
        result.setdefault("network", {})["languages"] = languages
    if latitude is not None:
        result.setdefault("network", {})["latitude"] = latitude
    if longitude is not None:
        result.setdefault("network", {})["longitude"] = longitude

    if cores is not None:
        result.setdefault("hardware", {})["cores"] = cores
    if memory is not None:
        result.setdefault("hardware", {})["memory"] = memory
    if screen:
        hw = result.setdefault("hardware", {})
        hw["screen_width"] = screen[0]
        hw["screen_height"] = screen[1]
        hw["avail_width"] = screen[0]
        hw["avail_height"] = screen[1] - 40

    if webgl_vendor:
        result.setdefault("webgl", {})["vendor"] = webgl_vendor
    if webgl_renderer:
        result.setdefault("webgl", {})["renderer"] = webgl_renderer

    if notes:
        result["notes"] = notes

    return result


def _load_country_locales() -> dict:
    global _COUNTRY_LOCALES
    if _COUNTRY_LOCALES is None:
        import json

        data_file = Path(__file__).parent / "data" / "country_locales.json"
        _COUNTRY_LOCALES = json.loads(data_file.read_text())
    return _COUNTRY_LOCALES


def _build_proxy_url(net) -> str | None:
    """Reconstruct full proxy URL with credentials for external requests."""
    if not net.proxy:
        return None
    parsed = urlparse(net.proxy)
    if net.proxy_username:
        auth = f"{net.proxy_username}:{net.proxy_password or ''}@"
        return f"{parsed.scheme}://{auth}{parsed.hostname}:{parsed.port}"
    return net.proxy


def _resolve_network(profile: Profile, data_dir: Path) -> Profile:
    """Resolve None network fields from GeoIP at launch time.

    With proxy  → resolve geo from proxy exit IP (timezone, locale, coordinates).
    Without proxy → resolve geo from public IP (timezone only).
    Explicit values in the profile are never overridden.
    """
    net = profile.network
    updates: dict = {}

    full_proxy = _build_proxy_url(net)
    geo = _lookup_exit_geo(full_proxy, data_dir)
    if geo:
        if net.timezone is None:
            updates["timezone"] = geo.timezone
        elif geo.timezone and net.timezone != geo.timezone:
            logger.warning(
                "Timezone mismatch: profile has %r but IP resolves to %r",
                net.timezone,
                geo.timezone,
            )

        # Locale, languages, coordinates — only when there's a proxy.
        if net.proxy:
            if net.locale is None or net.languages is None:
                country_map = _load_country_locales()
                info = country_map.get(geo.country_code)
                if info:
                    if net.locale is None:
                        updates["locale"] = info["locale"]
                    if net.languages is None:
                        updates["languages"] = info["languages"]

            if net.latitude is None and geo.latitude is not None:
                updates["latitude"] = round(geo.latitude + random.uniform(-0.01, 0.01), 6)
            if net.longitude is None and geo.longitude is not None:
                updates["longitude"] = round(geo.longitude + random.uniform(-0.01, 0.01), 6)

    # Fallback defaults for anything still None
    if net.timezone is None and "timezone" not in updates:
        updates["timezone"] = "UTC"
    if net.locale is None and "locale" not in updates:
        updates["locale"] = "en-US"
    if net.languages is None and "languages" not in updates:
        updates["languages"] = ["en-US", "en"]

    if not updates:
        return profile

    resolved_net = net.model_copy(update=updates)
    return profile.model_copy(update={"network": resolved_net})


def _lookup_exit_geo(proxy: str | None, data_dir: Path):
    """Look up GeoInfo for the exit IP — proxy if set, else public IP."""
    from dechromium._geoip import lookup, resolve_exit_ip, resolve_public_ip

    try:
        ip = resolve_exit_ip(proxy) if proxy else resolve_public_ip()
        if not ip:
            return None
        return lookup(ip, data_dir)
    except Exception:
        logger.debug("GeoIP lookup failed", exc_info=True)
        return None
