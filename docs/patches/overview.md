# Patches

All browser modifications are implemented as C++ patches applied to Chromium source code. No JavaScript injection. No CDP overrides.

Patches are stored in `patches/{chromium_version}/` as git format-patch files. Each patch is a single commit that modifies one fingerprinting vector.

## Current patches (Chromium 145.0.7632.116)

| # | Patch | What it does |
|---|---|---|
| 001 | `aspect-switches` | Declares all `--aspect-*` command-line switches and propagates them to renderer and utility processes |
| 002 | `navigator-webdriver` | `navigator.webdriver` returns `false` — patched in C++, not a CDP override |
| 003 | `navigator-platform` | `navigator.platform` returns value from `--aspect-platform` switch |
| 004 | `navigator-hardware` | `navigator.hardwareConcurrency` and `navigator.deviceMemory` from switches, with whitelist validation for deviceMemory |
| 005 | `screen-display` | Screen dimensions, color depth, DPR — patched at `WidgetBase::UpdateSurfaceAndScreenInfo()` level, covers both JS API and CSS media queries |
| 006 | `client-hints` | Overrides `GetUserAgentMetadata()` — single point covers both HTTP headers (Sec-CH-UA-*) and JS API (navigator.userAgentData) |
| 007 | `webgl-fingerprint` | Overrides `UNMASKED_VENDOR_WEBGL` and `UNMASKED_RENDERER_WEBGL` in getParameter(), WebGL params, extensions, and shader precision — covers WebGL 1 and 2 |
| 008 | `audio-fingerprint` | Noise in AudioBuffer.getChannelData(), copyFromChannel(), and all AnalyserNode getter methods |
| 009 | `network-privacy` | SOCKS5 RFC 1929 auth in C++, HTTP proxy auto-auth, DNS-over-HTTPS control, switch propagation to network utility process |
| 010 | `font-control` | Per-profile fontconfig via `FONTCONFIG_FILE`, blocks fontconfig substitution — if the requested font isn't installed, returns null instead of a substitute |
| 011 | `geolocation-spoofing` | Overrides `navigator.geolocation` coordinates via `--aspect-geo-latitude` / `--aspect-geo-longitude` switches, intercepted at `CreateGeoposition()` in blink |

## What's NOT patched (and why)

**TLS/JA3/JA4** — Chromium 145 produces identical TLS fingerprints to Chrome 145. Verified that `is_chrome_branded = false` doesn't affect TLS code.

**HTTP/2 SETTINGS** — Same as above. All constants (HEADER_TABLE_SIZE, INITIAL_WINDOW_SIZE, etc.) are identical to Chrome.

## How patches work

Each `--aspect-*` switch is read by `base::CommandLine::ForCurrentProcess()` inside the relevant C++ code. For example, `--aspect-platform=Win32` is read in `navigator_base.cc` where `navigator.platform` is implemented.

Some switches need to be **propagated** to child processes:

- **Renderer process** — switches propagated via `render_process_host_impl.cc`
- **Network utility process** — switches propagated via `chrome_content_browser_client.cc`
- **Environment variables** (FONTCONFIG_FILE, TZ, LANG) — inherited automatically via `fork()`

## Reading the patches

Each patch file is a standard `git format-patch` output. You can read them directly:
```bash
cat patches/145.0.7632.116/007-webgl-fingerprint.patch
```

Or apply them and browse the code:
```bash
export CHROMIUM_SRC=/path/to/chromium/src
./build/apply_patches.sh 145.0.7632.116
cd $CHROMIUM_SRC
git log --oneline 145.0.7632.116..aspect
```
