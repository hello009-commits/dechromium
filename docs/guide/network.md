# Proxy & Network

## Proxy

Supports SOCKS5, HTTP, and HTTPS proxies:
```python
# SOCKS5
dc.create("x", proxy="socks5://host:1080")

# SOCKS5 with auth
dc.create("x", proxy="socks5://user:pass@host:1080")

# HTTP with auth
dc.create("x", proxy="http://user:pass@host:8080")
```

Credentials are extracted from the URL automatically and passed to the browser via `--aspect-proxy-username` and `--aspect-proxy-password`. Authentication happens at the C++ level — no browser extension or CDP hack.

### DNS leak protection

When a proxy is configured, DNS resolution is forced through the proxy:
```
--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE {proxy_host}
```

The proxy host itself is excluded so the browser can connect to it.

### WebRTC leak protection

WebRTC is restricted to prevent IP leaks:
```
--force-webrtc-ip-handling-policy=disable_non_proxied_udp
```

Available policies:

| Policy | Enum | Description |
|---|---|---|
| `default` | `WebRTCPolicy.DEFAULT` | No restrictions |
| `default_public_and_private_interfaces` | `WebRTCPolicy.DEFAULT_PUBLIC_AND_PRIVATE` | Use default route + associated interfaces |
| `default_public_interface_only` | `WebRTCPolicy.DEFAULT_PUBLIC_INTERFACE_ONLY` | Only default route |
| `disable_non_proxied_udp` | `WebRTCPolicy.DISABLE_NON_PROXIED_UDP` | Force UDP through proxy (default) |

## Timezone
```python
dc.create("x", timezone="Asia/Tokyo")
```

Sets the `TZ` environment variable. Covers:

- `new Date().getTimezoneOffset()`
- `Intl.DateTimeFormat().resolvedOptions().timeZone`
- `new Date().toString()` timezone abbreviation

## Locale
```python
dc.create("x", locale="ja-JP", languages=["ja-JP", "ja", "en-US", "en"])
```

- `locale` → `--lang` flag + `LANG` env var → affects `Intl.*` APIs
- `languages` → `--accept-lang` flag → `navigator.languages` and `Accept-Language` header

## Geolocation

Spoof `navigator.geolocation` (both `getCurrentPosition` and `watchPosition`):
```python
dc.create("x", latitude=35.6762, longitude=139.6503)
```

When set, the browser receives `--aspect-geo-latitude` / `--aspect-geo-longitude` switches. The Chromium patch overrides the coordinates at the C++ level — no CDP hack, no permission prompt bypass needed (the user still grants permission normally, but receives spoofed coordinates).

If `latitude` and `longitude` are `None` (default), the geolocation API is not spoofed.

## Auto-detection

When you provide a proxy but **don't** set timezone, locale, or languages explicitly, dechromium automatically resolves the proxy IP and fills in matching values:

```python
# Proxy in Tokyo → timezone=Asia/Tokyo, locale=ja-JP, languages=["ja-JP","ja","en"],
#                   latitude=35.69, longitude=139.69
dc.create("x", proxy="socks5://tokyo-proxy:1080")
```

Auto-detection uses a local [DB-IP](https://db-ip.com/) City Lite database (MMDB format). The database is downloaded automatically on first use and cached in `~/.dechromium/data/geoip/`.

To manually download or update the database:
```bash
dechromium download-geoip
```

You can override any auto-detected value:
```python
# Use proxy geo for timezone/locale, but set custom coordinates
dc.create("x", proxy="socks5://tokyo-proxy:1080", latitude=35.6762, longitude=139.6503)

# Use proxy for geo, but force a specific timezone
dc.create("x", proxy="socks5://tokyo-proxy:1080", timezone="Asia/Osaka")
```

Auto-detection triggers only when **both** `timezone` and `locale` are not explicitly provided. Setting either one disables auto-detection entirely.

!!! note "DB-IP attribution"
    This product includes GeoLite2 Data created by DB-IP, available from
    [https://db-ip.com](https://db-ip.com). The database is updated monthly.

## Consistency

For anti-detect to work, network settings must be consistent:

- Proxy IP geolocation should match the timezone
- Timezone should match the locale (a Japanese locale with a US timezone is suspicious)
- Languages should include the locale's language

Auto-detection handles all of this automatically when you just provide a proxy.

## Upgrading existing profiles

Profiles created with an older library version may be missing newer auto-detection features (e.g., geolocation from proxy). Each profile stores the `library_version` it was created with.

Check which profiles need upgrading:
```bash
dechromium check
```

Upgrade all outdated profiles:
```bash
dechromium upgrade-profiles
```

This re-runs all auto-detection logic on existing profiles:

- Profiles with a proxy get geolocation, timezone, locale, and languages filled in (if still at defaults)
- Fields explicitly set by the user are never overwritten
- The profile's `library_version` is stamped with the current version

Via Python:
```python
# Check
for info in dc.check_profiles():
    print(info["name"], "outdated" if info["outdated"] else "ok")

# Upgrade
upgraded = dc.upgrade_profiles()
```
