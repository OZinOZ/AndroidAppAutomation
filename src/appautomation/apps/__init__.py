"""App drivers and the name -> class registry used by the runner."""

from __future__ import annotations

from typing import Dict, Type

from .base import App, AppNotReadyError
from .bolt import Bolt
from .google_maps import Google
from .indrive import InDrive

APP_REGISTRY: Dict[str, Type[App]] = {
    "bolt": Bolt,
    "indrive": InDrive,
    "google": Google,
}

__all__ = ["APP_REGISTRY", "App", "AppNotReadyError", "Bolt", "Google", "InDrive"]
