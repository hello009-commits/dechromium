from dechromium._client import Dechromium
from dechromium._config import Config
from dechromium._exceptions import (
    BrowserError,
    BrowserNotInstalledError,
    BrowserNotRunningError,
    BrowserTimeoutError,
    DechromiumError,
    DisplayError,
    ProfileExistsError,
    ProfileNotFoundError,
)
from dechromium._installer import BrowserManager, InstallError, install_chromium
from dechromium.browser import BrowserInfo
from dechromium.models import (
    ColorDepth,
    DeviceMemory,
    FontPack,
    Fonts,
    Hardware,
    Identity,
    Network,
    Noise,
    Platform,
    Profile,
    WebGL,
    WebRTCPolicy,
)

__version__ = "0.9.2"

__all__ = [
    "BrowserError",
    "BrowserInfo",
    "BrowserManager",
    "BrowserNotInstalledError",
    "BrowserNotRunningError",
    "BrowserTimeoutError",
    "ColorDepth",
    "Config",
    "Dechromium",
    "DechromiumError",
    "DeviceMemory",
    "DisplayError",
    "FontPack",
    "Fonts",
    "Hardware",
    "Identity",
    "InstallError",
    "Network",
    "Noise",
    "Platform",
    "Profile",
    "ProfileExistsError",
    "ProfileNotFoundError",
    "WebGL",
    "WebRTCPolicy",
    "install_chromium",
]
