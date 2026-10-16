"""Common base class of all app drivers."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import ClassVar, Tuple

from uiautomator2 import Device


class AppNotReadyError(RuntimeError):
    """Raised by a driver when the app cannot be used (e.g. not logged in)."""


class App(ABC):
    """Automates one app on one device for one route.

    Subclasses set :attr:`package` / :attr:`activity`, implement
    :meth:`get_info` and call :meth:`screenshot` at the points where fare or
    route information is visible.
    """

    #: Android package name.
    package: ClassVar[str] = ""
    #: Launch activity.
    activity: ClassVar[str] = ""
    #: Screenshot suffixes a successful run must produce (used to detect gaps).
    required_suffixes: ClassVar[Tuple[str, ...]] = ()

    def __init__(self, dev: Device, route_id: int, pickup: str, destination: str,
                 city: str, date: str, output_dir: str):
        self.dev = dev
        self.rid = route_id
        self.src = pickup
        self.dst = destination
        self.city = city
        self.date = date
        self.output = output_dir

    @abstractmethod
    def get_info(self) -> bool:
        """Drive the app and take screenshots. Return ``True`` on success."""

    def screenshot(self, suffix: str) -> str:
        """Save the current screen as ``<city><date><id:03d><suffix>.png``."""
        time.sleep(3)  # let animations settle
        path = os.path.join(self.output, f"{self.city}{self.date}{self.rid:03d}{suffix}.png")
        self.dev.screenshot(path)
        return path
