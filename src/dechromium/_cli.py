from __future__ import annotations

import sys


def main():
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        _usage()
        return

    cmd = args[0]
    if cmd == "install":
        _install(args[1:])
    elif cmd == "update":
        _update(args[1:])
    elif cmd == "browsers":
        _browsers(args[1:])
    elif cmd == "uninstall":
        _uninstall(args[1:])
    elif cmd == "serve":
        _serve(args[1:])
    elif cmd == "download-geoip":
        _download_geoip(args[1:])
    elif cmd == "version":
        from dechromium import __version__

        print(f"dechromium {__version__}")
    else:
        print(f"Unknown command: {cmd}")
        _usage()
        sys.exit(1)


def _install(args: list[str]):
    version = None
    force = False

    for arg in args:
        if arg == "--help":
            print("Usage: dechromium install [VERSION] [--force]")
            print()
            print("Download and install patched Chromium browser.")
            print()
            print("Arguments:")
            print("  VERSION              Chromium version (default: latest)")
            print()
            print("Options:")
            print("  --force              Re-download even if already installed")
            return
        elif arg.startswith("--version="):
            version = arg.split("=", 1)[1]
        elif arg == "--force":
            force = True
        elif not arg.startswith("-"):
            version = arg

    from dechromium._installer import install_chromium

    install_chromium(version=version, force=force)


def _update(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium update")
        print()
        print("Check for updates to installed browsers.")
        return

    from dechromium._installer import BrowserManager

    BrowserManager().update()


def _browsers(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium browsers")
        print()
        print("List available and installed browser versions.")
        return

    from dechromium._installer import BrowserManager, _version_key

    mgr = BrowserManager()
    installed = {e["version"] for e in mgr.installed()}

    print("Fetching available versions...")
    try:
        available = mgr.available()
    except Exception:
        available = []
        print("  Could not reach GitHub API.")

    all_versions = sorted(
        set(available) | installed,
        key=_version_key,
        reverse=True,
    )

    if not all_versions:
        print("No browsers available or installed.")
        return

    # Latest installed is active
    installed_sorted = sorted(installed, key=_version_key, reverse=True)
    active = installed_sorted[0] if installed_sorted else None

    print()
    print(f"  {'VERSION':<25} STATUS")
    for v in all_versions:
        status = ("installed *" if v == active else "installed") if v in installed else "available"
        print(f"  {v:<25} {status}")
    print()
    if active:
        print("  * = active (used by default)")


def _uninstall(args: list[str]):
    if not args or args[0] == "--help":
        print("Usage: dechromium uninstall VERSION")
        print()
        print("Remove an installed browser version.")
        return

    version = args[0]

    from dechromium._installer import BrowserManager

    if BrowserManager().uninstall(version):
        print(f"Uninstalled Chromium {version}")
    else:
        print(f"Chromium {version} is not installed.")
        sys.exit(1)


def _download_geoip(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium download-geoip")
        print()
        print("Download or update the GeoIP database (DB-IP City Lite).")
        print("Used for auto-detecting timezone/locale from proxy IP.")
        return

    from dechromium._config import _default_data_dir
    from dechromium._geoip import download

    data_dir = _default_data_dir()
    download(data_dir, progress=True)
    print("Done.")


def _serve(args: list[str]):
    host = "127.0.0.1"
    port = 3789

    for arg in args:
        if arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])

    from dechromium import Dechromium

    dc = Dechromium()
    try:
        dc.serve(host=host, port=port)
    except KeyboardInterrupt:
        pass
    finally:
        dc.stop_all()


def _usage():
    print("Usage: dechromium <command>")
    print()
    print("Browser management:")
    print("  install [VERSION] [--force]          Download patched Chromium")
    print("  update                               Check for browser updates")
    print("  browsers                             List available/installed browsers")
    print("  uninstall VERSION                    Remove installed browser")
    print()
    print("Data:")
    print("  download-geoip                       Download/update GeoIP database")
    print()
    print("Server:")
    print("  serve [--host=HOST] [--port=PORT]    Start REST API server")
    print()
    print("Info:")
    print("  version                              Show library version")
    print()
    print("Python library:")
    print("  from dechromium import Dechromium")
    print("  dc = Dechromium()")
    print('  profile = dc.create("my-profile", platform="windows")')
    print("  browser = dc.start(profile.id)")


if __name__ == "__main__":
    main()
