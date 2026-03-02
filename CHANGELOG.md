# Changelog

## 0.7.1

### Fixed

- Accept-Language header: remove q-values from `--accept-lang` (Chrome adds them internally; passing them caused malformed `en;q=0.9;q=0.8` headers)
- WebGL params: remove wrong `0x8073` → `SAMPLE_BUFFERS` mapping (0x8073 is `GL_MAX_3D_TEXTURE_SIZE`, not `GL_SAMPLE_BUFFERS`); was sending `SAMPLE_BUFFERS=2048` which is invalid
- WebGL params: skip unrecognized WebGL2-only hex-coded params that C++ switch cannot handle

## 0.7.0

Fingerprint audit — fix all critical, high and medium issues from BrowserScan analysis.

### Added

- `--aspect-font-families` flag — Blink-level font allowlist filtering (new patch 012)
- `--aspect-webgl-version` / `--aspect-webgl-glsl-version` flags — GL_VERSION string spoofing
- `font_families` field on `Fonts` model — per-platform font family lists
- `data/font_families.json` — Windows/macOS/Linux font family reference data
- WebGL `getExtension()` filtering — blocks extensions not in allowlist
- WebGL2 GL_VERSION/GLSL_VERSION spoofing
- Geolocation jitter (~1km) to avoid exact GeoIP center coordinates
- Auto-geo re-run in `update()` when proxy changes

### Changed

- Canvas noise: content-dependent FNV1a algorithm replacing edge-pixel-flip
- Audio noise: increased magnitude to detectable levels (5e-8 gain, 5e-5 analyser offset)
- DOMRect noise: `Scale()` instead of `Offset()` for proportional perturbation
- WebGL params format: `NAME=value` instead of `hex:value`
- `--window-size` uses `avail_height` instead of `screen_height`
- Accept-Language header uses `--accept-lang` with proper language tag list
- `avail_height` platform-aware taskbar deduction (Win: 40/48, Mac: 25, Linux: 27/36/48)
- SwiftShader: always enabled in headless mode (both platforms)
- Xvfb resolution matches profile screen dimensions
- WebGPU disabled via `--disable-features=WebGPUService`

### Removed

- `webgl_seed` from `Noise` model (was never used by C++ patches)

### Chromium patches

- Fixup 001: new switches (`kAspectFontFamilies`, `kAspectWebglVersion`, `kAspectWebglGlslVersion`)
- Fixup 005: content-dependent canvas noise (FNV1a PRNG, neighbor copy optimization)
- Fixup 006: GL_VERSION/GLSL spoofing, getExtension filtering, WebGL2 support
- Fixup 007: audio noise magnitude increase
- Fixup 008: DOMRect Scale instead of Offset
- New 012: font family allowlist in `font_cache.cc`

## 0.6.4

### Fixed

- `dechromium destroy` — added `uv pip uninstall` fallback for uv-managed environments

## 0.6.3

### Added

- `BrowserNotInstalledError` exception — clear error message when Chromium binary is not found, with install instructions

## 0.6.2

### Fixed

- `dechromium destroy` — fallback to `pip` CLI when `python -m pip` is unavailable (e.g. some venvs)
- Added `destroy` documentation to browser management guide

## 0.6.1

### Added

- `dechromium destroy [--yes]` CLI command — completely removes all data (profiles, browsers, fonts, geoip) and uninstalls the pip package

## 0.6.0

Profile versioning and upgrade system.

### Added

- `library_version` field on `Profile` — stamps the library version that created it
- `dechromium check` CLI command — shows which profiles are outdated
- `dechromium upgrade-profiles` CLI command — re-runs auto-detection on outdated profiles
- `Dechromium.check_profiles()` and `Dechromium.upgrade_profiles()` API methods
- `GET /check` and `POST /upgrade-profiles` server endpoints
- `_refresh_profile()` — generic refresh function for applying new auto-detection logic to existing profiles

### Changed

- `ProfileManager.create()` now stamps `library_version` with current `__version__`
- `_apply_overrides()` handles `library_version` field

## 0.5.0

Auto-geolocation from proxy IP and `navigator.geolocation` spoofing.

### Added

- GeoIP module (`_geoip.py`): DB-IP City Lite MMDB download and lookup
- Country → locale/languages mapping (`data/country_locales.json`, 250 countries)
- Auto-detection: `create()` fills timezone/locale/languages/geolocation from proxy IP when not explicitly provided
- `latitude` and `longitude` fields on `Network` model
- `--aspect-geo-latitude` / `--aspect-geo-longitude` launch arguments
- `dechromium download-geoip` CLI command
- `maxminddb>=2.0` dependency

### Chromium patches

- `011-geolocation-spoofing`: intercepts `CreateGeoposition()` in blink to override coordinates from command-line switches

## 0.4.0

Bundled fonts and context-manager-first documentation.

### Added

- Font packs bundled inside the pip package (`src/dechromium/fonts/`)
- Auto-install fonts on first use — no manual `cp -r fonts/` needed
- `.font_version` marker for fast-path skip and version-aware re-sync
- `_fonts.py` module with `ensure_fonts()` utility

### Changed

- Documentation uses `with Dechromium() as dc:` as the primary pattern
- Manual `dc.stop()` shown as alternative in quickstart
- Installation docs no longer require manual font copy step
- Repository structure: `fonts/` moved to `src/dechromium/fonts/`

## 0.3.0

Browser management and project standards.

### Added

- `dechromium install [VERSION]` — download patched Chromium from GitHub Releases
- `dechromium update` — check for updates to installed browsers (hotfix detection)
- `dechromium browsers` — list available and installed browser versions
- `dechromium uninstall VERSION` — remove installed browser
- `BrowserManager` class for programmatic browser management
- `Dechromium.install_browser()`, `.update_browsers()`, `.list_browsers()`, `.uninstall_browser()`
- Multi-version browser storage (`~/.dechromium/browsers/<version>/`)
- Auto-resolve latest installed browser as default
- SHA-256 verification when `manifest.json` is present in GitHub Release
- Compatibility check via `manifest.json` `min_library` field
- `.editorconfig`
- `.pre-commit-config.yaml` (trailing whitespace, EOF, YAML/TOML checks, ruff lint+format)
- `CLAUDE.md` — project guide for AI-assisted development
- `CONTRIBUTING.md` — contributor guide
- GitHub issue templates (bug report, feature request)
- GitHub pull request template

### Changed

- `Config.browser_bin` auto-resolves from `~/.dechromium/browsers/` (latest installed version)
- Legacy `~/.dechromium/browser/chrome` path still supported as fallback
- Added `pre-commit>=4.0` to dev dependencies

### Removed

- `_compat.py` — version compatibility is now handled by `manifest.json` in GitHub Releases, not hardcoded in the library

## 0.2.0

Package restructure and type safety improvements.

### Breaking changes

- **src/ layout** — package moved from `dechromium/` to `src/dechromium/` with subpackages
- **Enums replace strings** — `Platform`, `FontPack`, `WebRTCPolicy`, `DeviceMemory`, `ColorDepth` enums replace raw strings/numbers
- **Field renames** — `Hardware.memory_gb` is now `Hardware.memory` (DeviceMemory enum), `Hardware.device_pixel_ratio` is now `Hardware.pixel_ratio`
- **Custom exceptions** — `ProfileNotFoundError`, `BrowserError`, `BrowserTimeoutError` replace generic Python exceptions
- **CLI entry point** — `dechromium._cli:main` replaces `dechromium.__main__:main`

### Added

- `Platform`, `FontPack`, `WebRTCPolicy`, `DeviceMemory`, `ColorDepth` enums with IDE autocomplete and Pydantic validation
- `py.typed` marker (PEP 561)
- Custom exception hierarchy: `DechromiumError` base, `ProfileNotFoundError`, `ProfileExistsError`, `BrowserError`, `BrowserNotRunningError`, `BrowserTimeoutError`, `DisplayError`
- CI workflow (lint + test on Python 3.11, 3.12, 3.13)
- Release workflow (PyPI publish via Trusted Publishers)
- Reference docs for models, enums, exceptions, and configuration

### Changed

- Split flat package into subpackages: `models/`, `profile/`, `browser/`, `server/`
- Split `manager.py` into `profile/_manager.py`, `_launcher.py`, `_fontconfig.py`
- Split `browser.py` into `browser/_pool.py`, `_process.py`, `_display.py`
- Moved cookies to `browser/_cookies.py`
- Extracted `Dechromium` class from `__init__.py` to `_client.py`
- `Hardware.avail_width` / `avail_height` default to `None` (auto-computed from screen size)
- Updated `pyproject.toml` for hatch build with src/ layout
- Updated docs navigation with Reference section
- Fixed `repo_url` in mkdocs.yml to ENbanned/dechromium

## 0.1.0

Initial release.

### Chromium patches (145.0.7632.116)

- `navigator.webdriver` returns `false`
- `navigator.platform`, `hardwareConcurrency`, `deviceMemory` — spoofed via switches
- Screen properties — patched at WidgetBase level, covers JS API + CSS media queries
- Client Hints (Sec-CH-UA-Platform, etc.) — single patch point in `GetUserAgentMetadata()`
- Canvas fingerprint noise — deterministic per-seed
- WebGL vendor/renderer spoofing — covers WebGL 1 and 2
- Audio fingerprint noise — covers AudioBuffer and AnalyserNode
- SOCKS5/HTTP proxy auth — C++ level
- Font isolation — FONTCONFIG_FILE per-profile + strict match
- TLS/JA3 and HTTP/2 SETTINGS — verified identical to Chrome, no patch needed

### Python library

- Profile management with Pydantic v2 models
- Platform presets (windows, macos, linux)
- Browser process lifecycle with CDP readiness detection
- Font pack isolation via fontconfig
- Timezone/locale via environment variables
- Cookie import/export (Chrome SQLite format)
- Optional REST API via FastAPI
