from __future__ import annotations

import shutil
import time
from pathlib import Path

from dechromium._config import Config
from dechromium._exceptions import ProfileNotFoundError
from dechromium.models import Fonts, Hardware, Identity, Network, Noise, Profile, WebGL

from ._fontconfig import setup_profile_fonts
from ._launcher import build_launch_args, build_launch_env

_SECTION_MODELS = {
    "identity": Identity,
    "hardware": Hardware,
    "webgl": WebGL,
    "noise": Noise,
    "network": Network,
    "fonts": Fonts,
}


class ProfileManager:
    def __init__(self, config: Config):
        self.config = config
        self.config.profiles_dir.mkdir(parents=True, exist_ok=True)

    def create(self, name: str = "default", **overrides) -> Profile:
        from dechromium import __version__

        profile = Profile(name=name, library_version=__version__)
        _apply_overrides(profile, overrides)

        profile_dir = self._profile_dir(profile.id)
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir(profile.id).mkdir(exist_ok=True)
        setup_profile_fonts(profile, self.config)
        self._save(profile)
        return profile

    def get(self, profile_id: str) -> Profile:
        path = self._config_path(profile_id)
        if not path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_id}")
        return Profile.model_validate_json(path.read_text())

    def list_all(self) -> list[Profile]:
        result = []
        if not self.config.profiles_dir.exists():
            return result
        for pdir in sorted(self.config.profiles_dir.iterdir()):
            cfg = pdir / "profile.json"
            if cfg.exists():
                result.append(Profile.model_validate_json(cfg.read_text()))
        return result

    def update(self, profile_id: str, **overrides) -> Profile:
        profile = self.get(profile_id)
        profile.updated_at = int(time.time())
        _apply_overrides(profile, overrides)
        setup_profile_fonts(profile, self.config)
        self._save(profile)
        return profile

    def delete(self, profile_id: str) -> bool:
        pdir = self._profile_dir(profile_id)
        if not pdir.exists():
            return False
        shutil.rmtree(pdir)
        return True

    def launch_args(self, profile_id: str) -> list[str]:
        profile = self.get(profile_id)
        return build_launch_args(profile, self.config)

    def launch_env(self, profile_id: str) -> dict[str, str]:
        profile = self.get(profile_id)
        fonts_conf = self._fonts_conf_path(profile_id)
        if not fonts_conf.exists():
            setup_profile_fonts(profile, self.config)
        return build_launch_env(profile, self.config)

    def data_dir(self, profile_id: str) -> Path:
        return self._data_dir(profile_id)

    def _profile_dir(self, profile_id: str) -> Path:
        return self.config.profiles_dir / profile_id

    def _config_path(self, profile_id: str) -> Path:
        return self._profile_dir(profile_id) / "profile.json"

    def _data_dir(self, profile_id: str) -> Path:
        return self._profile_dir(profile_id) / "chrome_data"

    def _fonts_conf_path(self, profile_id: str) -> Path:
        return self._profile_dir(profile_id) / "fonts.conf"

    def _save(self, profile: Profile):
        self._config_path(profile.id).write_text(profile.model_dump_json(indent=2))


def _apply_overrides(profile: Profile, overrides: dict):
    for section_name, model_cls in _SECTION_MODELS.items():
        if section_name not in overrides:
            continue
        current = getattr(profile, section_name).model_dump()
        updates = overrides[section_name]
        if not isinstance(updates, dict):
            continue
        current.update(updates)
        if section_name == "identity" and "user_agent" not in updates:
            current["user_agent"] = ""
        setattr(profile, section_name, model_cls(**current))

    for field in ("name", "notes", "library_version"):
        if field in overrides:
            setattr(profile, field, overrides[field])
