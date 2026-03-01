from __future__ import annotations

import contextlib
from pathlib import Path
from urllib.parse import urlparse

from dechromium._config import Config
from dechromium._fonts import ensure_fonts
from dechromium._installer import BrowserManager
from dechromium.browser import BrowserInfo, BrowserPool
from dechromium.browser._cookies import export_cookies, import_cookies
from dechromium.models import Platform, Profile
from dechromium.profile import DiversityEngine, ProfileManager

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
        # Normalize platform enum to string
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

            # Auto-detect geo from proxy when timezone/locale not explicit
            if proxy and not timezone and not locale:
                _apply_auto_geo(overrides, proxy, self.config.data_dir)

            # Merge: generated is base, user overrides on top
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

            # Auto-detect geo from proxy when timezone/locale not explicit
            if proxy and not timezone and not locale:
                _apply_auto_geo(overrides, proxy, self.config.data_dir)

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
        args = self._manager.launch_args(profile_id)
        env = self._manager.launch_env(profile_id)
        return self._pool.start(
            profile_id,
            args,
            env,
            headless=headless,
            extra_args=extra_args,
            timeout=timeout,
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
        """Download and install patched Chromium.

        Args:
            version: Chromium version. If None, installs the latest from GitHub.
            force: Re-download even if already installed.
            progress: Show download progress.

        Returns:
            Path to the installed chrome binary.
        """
        return self._browsers.install(version, force=force, progress=progress)

    def update_browsers(self, *, progress: bool = True) -> list[str]:
        """Check for updates to installed browsers.

        Returns list of versions that were updated.
        """
        return self._browsers.update(progress=progress)

    def list_browsers(self) -> list[dict]:
        """List locally installed browser versions."""
        return self._browsers.installed()

    def uninstall_browser(self, version: str) -> bool:
        """Remove an installed Chromium version."""
        return self._browsers.uninstall(version)

    def check_profiles(self) -> list[dict]:
        """Check which profiles were created with an older library version.

        Returns list of dicts with profile info and whether it needs upgrading.
        """
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
        """Upgrade outdated profiles with latest auto-detection logic.

        Re-runs auto-geo for profiles with a proxy, stamps current library_version.

        Returns list of upgraded profile IDs.
        """
        from dechromium import __version__

        upgraded = []
        for profile in self._manager.list_all():
            if profile.library_version == __version__:
                continue

            changes = _refresh_profile(profile, self.config.data_dir)
            profile.library_version = __version__
            overrides: dict = {}
            if changes:
                overrides["network"] = changes
            overrides["library_version"] = __version__
            self._manager.update(profile.id, **overrides)

            if progress:
                detail = f" (updated: {', '.join(changes)})" if changes else ""
                print(f"  Upgraded {profile.name} ({profile.id}){detail}")
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


def _apply_auto_geo(overrides: dict, proxy: str, data_dir: Path) -> None:
    """Auto-fill timezone/locale/languages/geolocation from proxy IP."""
    import logging

    from dechromium._geoip import lookup, resolve_proxy_ip

    logger = logging.getLogger(__name__)

    try:
        ip = resolve_proxy_ip(proxy)
        geo = lookup(ip, data_dir)
    except Exception:
        logger.debug("Auto-geo failed for proxy %s", proxy, exc_info=True)
        return

    if not geo:
        return

    net = overrides.setdefault("network", {})
    if geo.timezone:
        net.setdefault("timezone", geo.timezone)

    country_map = _load_country_locales()
    info = country_map.get(geo.country_code)
    if info:
        net.setdefault("locale", info["locale"])
        net.setdefault("languages", info["languages"])

    net.setdefault("latitude", geo.latitude)
    net.setdefault("longitude", geo.longitude)


# -- Network defaults used to detect "user never set this" ------------------
_NET_DEFAULTS = {
    "timezone": "America/New_York",
    "locale": "en-US",
    "languages": ["en-US", "en"],
}


def _refresh_profile(profile: Profile, data_dir: Path) -> dict:
    """Re-run auto-detection logic on an existing profile.

    Returns a dict of network field changes to apply (empty if nothing to do).
    This function is generic — future auto-detection features should be added here.
    """
    import logging

    from dechromium._geoip import lookup, resolve_proxy_ip

    logger = logging.getLogger(__name__)
    changes: dict = {}
    net = profile.network

    # -- Auto-geo from proxy (added in 0.5.0) ------------------------------
    if net.proxy:
        try:
            ip = resolve_proxy_ip(net.proxy)
            geo = lookup(ip, data_dir)
        except Exception:
            logger.debug("refresh: geo lookup failed for %s", net.proxy, exc_info=True)
            geo = None

        if geo:
            # Fill None fields unconditionally
            if net.latitude is None and geo.latitude is not None:
                changes["latitude"] = geo.latitude
            if net.longitude is None and geo.longitude is not None:
                changes["longitude"] = geo.longitude

            # Replace default-valued fields (user never explicitly set them)
            if net.timezone == _NET_DEFAULTS["timezone"] and geo.timezone:
                changes["timezone"] = geo.timezone
            if net.locale == _NET_DEFAULTS["locale"]:
                country_map = _load_country_locales()
                info = country_map.get(geo.country_code)
                if info:
                    changes["locale"] = info["locale"]
                    if net.languages == _NET_DEFAULTS["languages"]:
                        changes["languages"] = info["languages"]

    # -- Future auto-detection features go here ----------------------------

    return changes
