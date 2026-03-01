from __future__ import annotations


def test_import():
    from dechromium import Dechromium, __version__

    assert __version__ == "0.5.0"
    assert Dechromium is not None


def test_installer_import():
    from dechromium import BrowserManager, InstallError, install_chromium

    assert BrowserManager is not None
    assert InstallError is not None
    assert install_chromium is not None
