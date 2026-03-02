from __future__ import annotations

from pydantic import BaseModel, Field


class WebGL(BaseModel):
    vendor: str = "Google Inc. (NVIDIA)"
    renderer: str = (
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )
    params: dict[str, int | float | list[int]] = Field(default_factory=dict)
    extensions: list[str] = Field(default_factory=list)
    shader_precision_high: list[int] = Field(default_factory=lambda: [127, 127, 23])
    shader_precision_medium: list[int] = Field(default_factory=lambda: [127, 127, 23])
