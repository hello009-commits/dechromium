# Models & Enums

## Enums

### Platform
```python
from dechromium import Platform

Platform.WINDOWS   # "windows"
Platform.MACOS     # "macos"
Platform.LINUX     # "linux"
```

### DeviceMemory
```python
from dechromium import DeviceMemory

DeviceMemory.GB_0_25  # 0.25
DeviceMemory.GB_0_5   # 0.5
DeviceMemory.GB_1     # 1
DeviceMemory.GB_2     # 2
DeviceMemory.GB_4     # 4
DeviceMemory.GB_8     # 8
```

Valid `navigator.deviceMemory` values per W3C spec. Any other value is a detection flag.

### ColorDepth
```python
from dechromium import ColorDepth

ColorDepth.BIT_24  # 24
ColorDepth.BIT_30  # 30
ColorDepth.BIT_48  # 48
```

### FontPack
```python
from dechromium import FontPack

FontPack.WINDOWS  # "windows"
FontPack.MACOS    # "macos"
FontPack.LINUX    # "linux"
```

### WebRTCPolicy
```python
from dechromium import WebRTCPolicy

WebRTCPolicy.DEFAULT                     # "default"
WebRTCPolicy.DISABLE_NON_PROXIED_UDP     # "disable_non_proxied_udp"
WebRTCPolicy.DEFAULT_PUBLIC_INTERFACE_ONLY  # "default_public_interface_only"
WebRTCPolicy.DEFAULT_PUBLIC_AND_PRIVATE   # "default_public_and_private_interfaces"
```

## Models

All models are Pydantic v2 `BaseModel` subclasses with validation.

### Identity

| Field | Type | Default | Description |
|---|---|---|---|
| `chrome_version` | `int` | `145` | Chrome version in user agent |
| `platform` | `str` | `"Win32"` | `navigator.platform` |
| `ua_platform` | `str` | `"Windows"` | `Sec-CH-UA-Platform` |
| `ua_platform_version` | `str` | `"15.0.0"` | `Sec-CH-UA-Platform-Version` |
| `ua_arch` | `str` | `"x86"` | `Sec-CH-UA-Arch` |
| `user_agent` | `str` | auto-generated | Full user agent string |

### Hardware

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `cores` | `int` | `8` | 1-32 | `navigator.hardwareConcurrency` |
| `memory` | `DeviceMemory` | `GB_8` | enum only | `navigator.deviceMemory` |
| `screen_width` | `int` | `1920` | 800-3840 | `screen.width` |
| `screen_height` | `int` | `1080` | 600-2160 | `screen.height` |
| `avail_width` | `int \| None` | `None` | auto = screen_width | `screen.availWidth` |
| `avail_height` | `int \| None` | `None` | auto = screen_height - 40 | `screen.availHeight` |
| `color_depth` | `ColorDepth` | `BIT_24` | enum only | `screen.colorDepth` |
| `pixel_ratio` | `float` | `1.0` | 1.0-3.0 | `window.devicePixelRatio` |

### WebGL

| Field | Type | Default | Description |
|---|---|---|---|
| `vendor` | `str` | `"Google Inc. (NVIDIA)"` | `UNMASKED_VENDOR_WEBGL` |
| `renderer` | `str` | NVIDIA RTX 3060 D3D11 | `UNMASKED_RENDERER_WEBGL` |
| `params` | `dict[str, int \| list[int]]` | `{}` | WebGL parameter overrides (hex enum → value) |
| `extensions` | `list[str]` | `[]` | Supported WebGL extensions |
| `shader_precision_high` | `list[int]` | `[127, 127, 23]` | highp precision [rangeMin, rangeMax, precision] |
| `shader_precision_medium` | `list[int]` | `[127, 127, 23]` | mediump precision |

### Noise

| Field | Type | Default | Description |
|---|---|---|---|
| `canvas_seed` | `str` | auto (12-char hex) | Canvas fingerprint noise seed |
| `audio_seed` | `str` | auto (12-char hex) | Audio fingerprint noise seed |
| `clientrects_seed` | `str` | auto (12-char hex) | DOMRect noise seed |
| `webgl_seed` | `str` | auto (12-char hex) | WebGL noise seed |

### Network

| Field | Type | Default | Description |
|---|---|---|---|
| `proxy` | `str` | `""` | Proxy URL (socks5://..., http://...) |
| `proxy_username` | `str` | `""` | Proxy auth username |
| `proxy_password` | `str` | `""` | Proxy auth password |
| `webrtc_policy` | `WebRTCPolicy` | `DISABLE_NON_PROXIED_UDP` | WebRTC IP handling policy |
| `timezone` | `str` | `"America/New_York"` | IANA timezone |
| `locale` | `str` | `"en-US"` | BCP 47 locale tag |
| `languages` | `list[str]` | `["en-US", "en"]` | Accept-Language / navigator.languages |
| `latitude` | `float \| None` | `None` | Geolocation spoof latitude (-90 to 90) |
| `longitude` | `float \| None` | `None` | Geolocation spoof longitude (-180 to 180) |

### Fonts

| Field | Type | Default | Description |
|---|---|---|---|
| `font_pack` | `FontPack` | `WINDOWS` | Which font pack to use |

### Profile

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | auto (12-char hex) | Unique profile identifier |
| `name` | `str` | `"default"` | Human-readable name |
| `created_at` | `int` | auto (unix timestamp) | Creation time |
| `updated_at` | `int` | auto (unix timestamp) | Last update time |
| `notes` | `str` | `""` | User notes |
| `library_version` | `str` | `"0.0.0"` | Library version that created/upgraded this profile |
| `identity` | `Identity` | defaults | Navigator identity |
| `hardware` | `Hardware` | defaults | Hardware specs |
| `webgl` | `WebGL` | defaults | WebGL configuration |
| `noise` | `Noise` | defaults | Fingerprint noise seeds |
| `network` | `Network` | defaults | Network settings |
| `fonts` | `Fonts` | defaults | Font configuration |
