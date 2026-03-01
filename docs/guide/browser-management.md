# Browser Management

Manage patched Chromium installations — download, update, list, and remove browser versions.

## CLI

### Install

```bash
dechromium install                       # latest version from GitHub
dechromium install 145.0.7632.116        # specific version
dechromium install 145.0.7632.116 --force  # re-download even if installed
```

### List

```bash
dechromium browsers
```

```
  VERSION                   STATUS
  146.0.8000.50             available
  145.0.7632.116            installed *

  * = active (used by default)
```

### Update

```bash
dechromium update
```

Checks each installed browser against GitHub. If a binary was re-uploaded (hotfix), re-downloads it.

### Uninstall

```bash
dechromium uninstall 145.0.7632.116
```

## Python API

```python
from dechromium import Dechromium

dc = Dechromium()

# Install
dc.install_browser()                         # latest
dc.install_browser("145.0.7632.116")         # specific

# List installed
for entry in dc.list_browsers():
    print(entry["version"])

# Update
updated = dc.update_browsers()

# Uninstall
dc.uninstall_browser("145.0.7632.116")
```

Or use `BrowserManager` directly:
```python
from dechromium import BrowserManager

mgr = BrowserManager()
mgr.install("145.0.7632.116")
mgr.available()     # list versions on GitHub
mgr.installed()     # list local versions
mgr.update()        # check for hotfixes
mgr.uninstall("145.0.7632.116")
```

## Multi-version storage

Each version is installed to its own directory:
```
~/.dechromium/browsers/
├── 145.0.7632.116/
│   ├── chrome
│   └── .manifest.json
└── 146.0.8000.50/
    ├── chrome
    └── .manifest.json
```

The library auto-selects the latest installed version. Override with `DECHROMIUM_BROWSER_BIN` or `Config(browser_bin=...)`.

## How updates work

Each GitHub Release has an `updated_at` timestamp per asset. When you run `dechromium update`:

1. For each installed version, fetch the release from GitHub
2. Compare the remote `updated_at` with the locally stored value in `.manifest.json`
3. If the remote is newer (patch was re-built and re-uploaded), re-download

### Destroy

Completely remove dechromium — all data and the pip package:

```bash
dechromium destroy
```

This deletes:

- `~/.dechromium/` — all profiles, browsers, fonts, GeoIP data
- The `dechromium` pip package itself

Requires confirmation. Use `--yes` to skip the prompt:
```bash
dechromium destroy --yes
```

## SHA-256 verification

If a `manifest.json` asset is present in the GitHub Release, the installer:

1. Downloads `manifest.json` first (small, instant)
2. Checks `min_library` — warns if the library version is too old
3. Downloads the binary
4. Verifies `sha256` from the manifest against the downloaded file
