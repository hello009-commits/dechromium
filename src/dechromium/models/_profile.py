from __future__ import annotations

import time
import uuid

from pydantic import BaseModel, Field

from ._fonts import Fonts
from ._hardware import Hardware
from ._identity import Identity
from ._network import Network
from ._noise import Noise
from ._webgl import WebGL


def _hex12() -> str:
    return uuid.uuid4().hex[:12]


def _ts() -> int:
    return int(time.time())


class Profile(BaseModel):
    id: str = Field(default_factory=_hex12)
    name: str = "default"
    created_at: int = Field(default_factory=_ts)
    updated_at: int = Field(default_factory=_ts)
    notes: str = ""
    library_version: str = "0.0.0"
    identity: Identity = Field(default_factory=Identity)
    hardware: Hardware = Field(default_factory=Hardware)
    webgl: WebGL = Field(default_factory=WebGL)
    noise: Noise = Field(default_factory=Noise)
    network: Network = Field(default_factory=Network)
    fonts: Fonts = Field(default_factory=Fonts)
