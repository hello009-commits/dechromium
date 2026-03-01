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
    elif cmd == "check":
        _check(args[1:])
    elif cmd == "upgrade-profiles":
        _upgrade_profiles(args[1:])
    elif cmd == "destroy":
        _destroy(args[1:])
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


def _check(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium check")
        print()
        print("Check which profiles need upgrading.")
        print("Profiles created with an older library version may be missing")
        print("features like auto-geolocation from proxy IP.")
        return

    from dechromium import Dechromium

    dc = Dechromium()
    results = dc.check_profiles()

    if not results:
        print("No profiles found.")
        return

    outdated = [r for r in results if r["outdated"]]

    print()
    print(f"  {'NAME':<20} {'ID':<14} {'VERSION':<12} STATUS")
    for r in results:
        status = "outdated" if r["outdated"] else "up to date"
        print(f"  {r['name']:<20} {r['id']:<14} {r['library_version']:<12} {status}")
    print()
    if outdated:
        print(f"  {len(outdated)} profile(s) can be upgraded.")
        print("  Run: dechromium upgrade-profiles")
    else:
        print("  All profiles are up to date.")


def _upgrade_profiles(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium upgrade-profiles")
        print()
        print("Upgrade outdated profiles with latest auto-detection logic.")
        print("Re-runs geo-detection for profiles with a proxy, fills missing fields,")
        print("and stamps the current library version.")
        return

    from dechromium import Dechromium

    dc = Dechromium()
    results = dc.check_profiles()
    outdated = [r for r in results if r["outdated"]]

    if not outdated:
        print("All profiles are up to date.")
        return

    print(f"Upgrading {len(outdated)} profile(s)...")
    upgraded = dc.upgrade_profiles(progress=True)
    print(f"\nDone. {len(upgraded)} profile(s) upgraded.")


def _destroy(args: list[str]):
    if args and args[0] == "--help":
        print("Usage: dechromium destroy [--yes]")
        print()
        print("Completely remove dechromium: all data, profiles, browsers,")
        print("and the pip package itself.")
        print()
        print("Options:")
        print("  --yes    Skip confirmation prompt")
        return

    import shutil
    import subprocess

    from dechromium._config import _default_data_dir

    data_dir = _default_data_dir()
    skip_confirm = "--yes" in args

    print("This will permanently delete:")
    print(f"  {data_dir}/            (profiles, browsers, fonts, geoip)")
    print("  dechromium pip package")
    print()

    if not skip_confirm:
        answer = input("Are you sure? Type 'yes' to confirm: ")
        if answer.strip().lower() != "yes":
            print("Aborted.")
            return

    # 1. Remove data directory
    if data_dir.exists():
        shutil.rmtree(data_dir)
        print(f"  Removed {data_dir}")
    else:
        print(f"  {data_dir} does not exist, skipping")

    # 2. Uninstall pip package (must be last — we're running from it)
    print("  Uninstalling dechromium package...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "dechromium", "-y"],
        capture_output=True,
    )
    if result.returncode != 0:
        # Fallback: pip may not be installed as module in this env
        subprocess.run(["pip", "uninstall", "dechromium", "-y"], check=False)
    print()
    print("dechromium has been completely removed.")


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
    print("Profiles:")
    print("  check                                Check profiles for available upgrades")
    print("  upgrade-profiles                     Upgrade outdated profiles")
    print()
    print("Data:")
    print("  download-geoip                       Download/update GeoIP database")
    print()
    print("Server:")
    print("  serve [--host=HOST] [--port=PORT]    Start REST API server")
    print()
    print("Info:")
    print("  version                              Show library version")
    print("  destroy [--yes]                      Remove all data + uninstall package")
    print()
    print("Python library:")
    print("  from dechromium import Dechromium")
    print("  dc = Dechromium()")
    print('  profile = dc.create("my-profile", platform="windows")')
    print("  browser = dc.start(profile.id)")


if __name__ == "__main__":
    main()
