from __future__ import annotations

import sys
from urllib.parse import urlparse

from dechromium._config import Config
from dechromium.models import Profile

_GL_PARAM_NAMES = {
    "0D33": "MAX_TEXTURE_SIZE",
    "851C": "MAX_CUBE_MAP_TEXTURE_SIZE",
    "84E8": "MAX_RENDERBUFFER_SIZE",
    "0D3D": "MAX_VIEWPORT_DIMS",
    "8872": "MAX_TEXTURE_IMAGE_UNITS",
    "8B4D": "MAX_COMBINED_TEXTURE_IMAGE_UNITS",
    "8869": "MAX_VERTEX_ATTRIBS",
    "8B4C": "MAX_VERTEX_TEXTURE_IMAGE_UNITS",
    "8DFB": "MAX_VERTEX_UNIFORM_VECTORS",
    "8DFD": "MAX_FRAGMENT_UNIFORM_VECTORS",
    "8DFC": "MAX_VARYING_VECTORS",
    "846E": "ALIASED_LINE_WIDTH_RANGE",
    "846D": "ALIASED_POINT_SIZE_RANGE",
    "0D50": "SUBPIXEL_BITS",
    "0D52": "RED_BITS",
    "0D53": "GREEN_BITS",
    "0D54": "BLUE_BITS",
    "0D55": "ALPHA_BITS",
    "0D56": "DEPTH_BITS",
    "0D57": "STENCIL_BITS",
}


def build_launch_args(profile: Profile, config: Config) -> list[str]:
    """Build Chrome command-line arguments for a profile."""
    net = profile.network
    hw = profile.hardware
    ident = profile.identity
    wgl = profile.webgl
    data_dir = config.profiles_dir / profile.id / "chrome_data"

    # --accept-lang takes plain language tags; Chrome adds q-values internally
    _accept_lang = ",".join(net.languages[:5]) if net.languages else net.locale

    args = [
        str(config.browser_bin),
        f"--user-data-dir={data_dir}",
        f"--user-agent={ident.user_agent}",
        f"--lang={net.locale}",
        f"--accept-lang={_accept_lang}",
        f"--window-size={hw.avail_width},{hw.avail_height}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=AsyncDns,DnsOverHttps,DnsHttpssvc,WebGPUService",
        "--dns-over-https-mode=off",
        "--disable-domain-reliability",
        "--disable-background-networking",
        "--no-pings",
    ]

    if net.proxy:
        args.append(f"--proxy-server={net.proxy}")
        proxy_host = urlparse(net.proxy).hostname or ""
        resolver_rules = f"MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE {proxy_host}"
        args.append(f"--host-resolver-rules={resolver_rules}")
        args.append(f"--force-webrtc-ip-handling-policy={net.webrtc_policy.value}")
        if net.proxy_username:
            args.append(f"--aspect-proxy-username={net.proxy_username}")
        if net.proxy_password:
            args.append(f"--aspect-proxy-password={net.proxy_password}")

    canvas_seed = int(profile.noise.canvas_seed, 16)
    audio_seed = int(profile.noise.audio_seed, 16)
    domrect_seed = int(profile.noise.clientrects_seed, 16)

    args.extend(
        [
            f"--aspect-platform={ident.platform}",
            f"--aspect-hardware-concurrency={hw.cores}",
            f"--aspect-device-memory={float(hw.memory)}",
            f"--aspect-screen-width={hw.screen_width}",
            f"--aspect-screen-height={hw.screen_height}",
            f"--aspect-screen-avail-width={hw.avail_width}",
            f"--aspect-screen-avail-height={hw.avail_height}",
            f"--aspect-color-depth={int(hw.color_depth)}",
            f"--aspect-device-pixel-ratio={hw.pixel_ratio}",
            f"--aspect-ua-platform={ident.ua_platform}",
            f"--aspect-ua-platform-version={ident.ua_platform_version}",
            f"--aspect-ua-arch={ident.ua_arch}",
            f"--aspect-canvas-noise-seed={canvas_seed}",
            f"--aspect-audio-noise-seed={audio_seed}",
            f"--aspect-domrect-noise-seed={domrect_seed}",
            f"--aspect-webgl-vendor={wgl.vendor}",
            f"--aspect-webgl-renderer={wgl.renderer}",
        ]
    )

    # WebGL version strings (hide SwiftShader identity)
    args.append("--aspect-webgl-version=WebGL 1.0 (OpenGL ES 3.0 Chromium)")
    args.append("--aspect-webgl-glsl-version=WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 3.0 Chromium)")

    if wgl.params:
        pairs = []
        for enum_hex, val in wgl.params.items():
            name = _GL_PARAM_NAMES.get(enum_hex.upper())
            if name is None:
                continue  # skip WebGL2-only params not handled by C++ switch
            if isinstance(val, list):
                if name in ("MAX_VIEWPORT_DIMS",):
                    pairs.append(f"{name}={val[0]}x{val[1]}")
                elif name in ("ALIASED_LINE_WIDTH_RANGE", "ALIASED_POINT_SIZE_RANGE"):
                    pairs.append(f"{name}={val[0]}-{val[1]}")
                else:
                    pairs.append(f"{name}={'x'.join(str(v) for v in val)}")
            else:
                pairs.append(f"{name}={val}")
        args.append(f"--aspect-webgl-params={','.join(pairs)}")

    if wgl.extensions:
        args.append(f"--aspect-webgl-extensions={','.join(wgl.extensions)}")

    if wgl.shader_precision_high:
        args.append(
            f"--aspect-webgl-precision-high="
            f"{wgl.shader_precision_high[0]},"
            f"{wgl.shader_precision_high[1]},"
            f"{wgl.shader_precision_high[2]}"
        )
    if wgl.shader_precision_medium:
        args.append(
            f"--aspect-webgl-precision-medium="
            f"{wgl.shader_precision_medium[0]},"
            f"{wgl.shader_precision_medium[1]},"
            f"{wgl.shader_precision_medium[2]}"
        )

    if net.latitude is not None and net.longitude is not None:
        args.append(f"--aspect-geo-latitude={net.latitude}")
        args.append(f"--aspect-geo-longitude={net.longitude}")

    # Font family allowlist (Blink-level filtering)
    if profile.fonts.font_families:
        args.append(f"--aspect-font-families={','.join(profile.fonts.font_families)}")

    return args


def build_launch_env(profile: Profile, config: Config) -> dict[str, str]:
    """Build environment variables for launching Chrome."""
    env: dict[str, str] = {"TZ": profile.network.timezone}
    if sys.platform != "win32":
        fonts_conf = config.profiles_dir / profile.id / "fonts.conf"
        posix_locale = profile.network.locale.replace("-", "_") + ".UTF-8"
        env["FONTCONFIG_FILE"] = str(fonts_conf)
        env["LANG"] = posix_locale
    return env
