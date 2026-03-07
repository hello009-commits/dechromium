from __future__ import annotations

import sys
from urllib.parse import urlparse

from dechromium._config import Config
from dechromium.models import Profile


def build_launch_args(profile: Profile, config: Config, *, headless: bool = True) -> list[str]:
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
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=AsyncDns,DnsOverHttps,DnsHttpssvc,WebGPUService",
        "--dns-over-https-mode=off",
        "--disable-domain-reliability",
        "--disable-background-networking",
        "--no-pings",
        "--force-color-profile=srgb",
        "--blink-settings=preferredColorScheme=1",
    ]

    # In headless mode, force window to match spoofed screen (virtual display).
    # In headed mode, let Chrome auto-size to the real monitor.
    if headless:
        args.append(f"--window-size={hw.avail_width},{hw.avail_height}")

    if net.proxy:
        args.append(f"--proxy-server={net.proxy}")
        proxy_host = urlparse(net.proxy).hostname or ""
        resolver_rules = f"MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE {proxy_host}"
        args.append(f"--host-resolver-rules={resolver_rules}")
        if net.proxy_username:
            args.append(f"--aspect-proxy-username={net.proxy_username}")
        if net.proxy_password:
            args.append(f"--aspect-proxy-password={net.proxy_password}")

    # Always set WebRTC policy (default: disable_non_proxied_udp = no ICE candidates)
    args.append(f"--webrtc-ip-handling-policy={net.webrtc_policy.value}")

    # Block port scanning on localhost (BrowserScan probes 3389, 5900, etc.)
    args.append("--aspect-block-local-ports=3389,5900,5800,8080,8443,9100")

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
            f"--aspect-screen-avail-top={hw.avail_top}",
        ]
    )

    # Scrollbar style: overlay for macOS (0px), fluent for Windows/Linux (15px)
    scrollbar_style = "overlay" if ident.platform == "MacIntel" else "fluent"
    args.append(f"--aspect-scrollbar-style={scrollbar_style}")

    # system-ui CSS generic → platform-appropriate font
    _system_ui = {"Win32": "Segoe UI", "MacIntel": "SF Pro", "Linux x86_64": "DejaVu Sans"}
    args.append(f"--system-font-family={_system_ui.get(ident.platform, 'Arial')}")

    # WebGPU preferred canvas format (platform-dependent)
    preferred_fmt = "bgra8unorm" if ident.platform != "Linux x86_64" else "rgba8unorm"
    args.append(f"--aspect-webgpu-preferred-format={preferred_fmt}")

    # Timezone spoofing (ICU override on Windows, env var on Linux)
    if net.timezone:
        args.append(f"--aspect-timezone={net.timezone}")

    # WebGL version strings — send inner driver portion only; C++ constructs
    # the correct "WebGL 1.0 (...)" / "WebGL 2.0 (...)" prefix per context.
    args.append("--aspect-webgl-version=OpenGL ES 3.0 Chromium")
    args.append("--aspect-webgl-glsl-version=OpenGL ES GLSL ES 3.0 Chromium")

    # WebGL params — hex-based format: "0D33=16384,0D3A=32767x32767,..."
    # C++ parses hex GLenum keys directly, no name mapping needed.
    if wgl.params:
        pairs = []
        for enum_hex, val in wgl.params.items():
            key = enum_hex.upper()
            if isinstance(val, list):
                if len(val) == 2:
                    # Array params: WxH for int arrays, min-max for float ranges
                    # Use 'x' for int pairs, '-' for float ranges
                    int_hex = key.upper()
                    # 846D = ALIASED_POINT_SIZE_RANGE, 846E = ALIASED_LINE_WIDTH_RANGE
                    if int_hex in ("846D", "846E"):
                        pairs.append(f"{key}={val[0]}-{val[1]}")
                    else:
                        pairs.append(f"{key}={val[0]}x{val[1]}")
                else:
                    pairs.append(f"{key}={'x'.join(str(v) for v in val)}")
            else:
                pairs.append(f"{key}={val}")
        args.append(f"--aspect-webgl-params={','.join(pairs)}")

    if wgl.extensions:
        args.append(f"--aspect-webgl-extensions={','.join(wgl.extensions)}")

    if wgl.shader_precision_float:
        args.append(
            f"--aspect-webgl-precision-float="
            f"{wgl.shader_precision_float[0]},"
            f"{wgl.shader_precision_float[1]},"
            f"{wgl.shader_precision_float[2]}"
        )
    if wgl.shader_precision_int:
        args.append(
            f"--aspect-webgl-precision-int="
            f"{wgl.shader_precision_int[0]},"
            f"{wgl.shader_precision_int[1]},"
            f"{wgl.shader_precision_int[2]}"
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
        env["GTK_THEME"] = "Adwaita"
    return env
