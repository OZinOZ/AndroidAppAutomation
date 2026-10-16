"""Configuration loading.

All machine specific values (device serials, e-mail addresses, tool paths)
live in a YAML file that is *not* part of the repository. Copy
``config.example.yaml`` to ``config.yaml`` and edit it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

CONFIG_ENV_VAR = "APPAUTOMATION_CONFIG"
DEFAULT_CONFIG_NAME = "config.yaml"


@dataclass
class PhoneConfig:
    """One physical Android device."""
    serial: str                 # `adb devices` serial number
    profile: str = "hd720"      # key of constants.SCREEN_PROFILES


@dataclass
class EmailConfig:
    """Gmail API notification settings (optional)."""
    sender: str
    recipient: str
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"


@dataclass
class Config:
    """Application configuration."""
    work_base: Path
    phones: Dict[str, PhoneConfig]
    adb_path: str = "adb"
    tesseract_cmd: Optional[str] = None
    ocr_engine: str = "auto"    # auto | easyocr | paddleocr | tesseract
    ocr_gpu: bool = True
    partial_routes: List[int] = field(default_factory=list)
    email: Optional[EmailConfig] = None

    def phone(self, alias: str) -> PhoneConfig:
        try:
            return self.phones[alias]
        except KeyError:
            known = ", ".join(sorted(self.phones)) or "<none>"
            raise KeyError(f"Unknown phone '{alias}'. Configured phones: {known}") from None


def find_config(explicit: Optional[str] = None) -> Path:
    """Locate the config file: ``--config`` > ``$APPAUTOMATION_CONFIG`` > ``./config.yaml``."""
    candidate = explicit or os.environ.get(CONFIG_ENV_VAR) or DEFAULT_CONFIG_NAME
    path = Path(candidate).expanduser()
    if not path.is_file():
        raise FileNotFoundError(
            f"Config file '{path}' not found. Copy config.example.yaml to config.yaml "
            f"or pass --config / set ${CONFIG_ENV_VAR}."
        )
    return path


def load_config(explicit: Optional[str] = None) -> Config:
    """Read and validate the YAML configuration."""
    with open(find_config(explicit), encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    phones = {
        alias.lower(): PhoneConfig(serial=str(p["serial"]), profile=p.get("profile", "hd720"))
        for alias, p in (raw.get("phones") or {}).items()
    }
    email_raw = raw.get("email")
    email = EmailConfig(**email_raw) if email_raw else None

    return Config(
        work_base=Path(raw.get("work_base", "workspace")).expanduser(),
        phones=phones,
        adb_path=raw.get("adb_path", "adb"),
        tesseract_cmd=raw.get("tesseract_cmd"),
        ocr_engine=raw.get("ocr_engine", "auto"),
        ocr_gpu=bool(raw.get("ocr_gpu", True)),
        partial_routes=[int(i) for i in raw.get("partial_routes", [])],
        email=email,
    )
