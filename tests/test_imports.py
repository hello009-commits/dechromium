from __future__ import annotations


def test_import():
    from importlib.metadata import version

    from dechromium import Dechromium, __version__

    assert __version__ == version("dechromium")
    assert Dechromium is not None


def test_installer_import():
    from dechromium import BrowserManager, InstallError, install_chromium

    assert BrowserManager is not None
    assert InstallError is not None
    assert install_chromium is not None
