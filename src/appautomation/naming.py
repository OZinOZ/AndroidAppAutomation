"""Task-name and address helpers (city codes, search addresses, file names)."""

from __future__ import annotations

import os
from typing import Tuple

from .constants import (
    CITY_COUNTRIES, CITY_NAMES, CITY_STATES, PREFIXES, SERVICES, TASK_APPS,
)

CITY_BY_NAME = {name: code for code, name in CITY_NAMES.items()}


def get_city_name(task: str) -> str:
    """Return the 3-letter city code embedded in a task name.

    >>> get_city_name("BOLT_NYC")
    'NYC'
    >>> get_city_name("MIA_DROPOFF")
    'SUN'
    """
    parts = task.split("_")
    if parts[0] in PREFIXES:
        start = len(parts[0]) + 1
        return task[start:start + 3]
    if parts[-1] in SERVICES:
        return task[:3]
    return task


def get_city_path(task: str) -> str:
    """Strip an app prefix to get the route-file name (``BOLT_NYC`` -> ``NYC``)."""
    parts = task.split("_")
    if parts[0] in PREFIXES:
        return task[len(parts[0]) + 1:]
    return task


def get_task_key(task: str) -> str:
    """Pick the key of :data:`TASK_APPS` that applies to ``task``."""
    parts = task.split("_")
    for candidate in (parts[0], parts[-1]):
        if candidate in TASK_APPS:
            return candidate
    return "DEFAULT"


def address_adapt(origin: str, task: str) -> str:
    """Expand a short address with state / city / country for map searches."""
    abbr = get_city_name(task)
    if abbr not in CITY_NAMES:
        new_addr = origin
    else:
        new_addr = ",".join([CITY_STATES.get(abbr, ""), origin, CITY_NAMES[abbr]])
    country = CITY_COUNTRIES.get(abbr)
    if country and country not in new_addr:
        new_addr += "," + country
    return new_addr


def address_origin(adapted: str, city: str) -> str:
    """Undo :func:`address_adapt`'s city suffix."""
    if city in CITY_NAMES and CITY_NAMES[city] in adapted:
        return adapted.removesuffix("," + CITY_NAMES[city])
    return adapted


def get_record_range(start: int, end: int, now_hour: int) -> Tuple[int, int]:
    """Translate the magic ``start`` values 400 / 404 / 900 into a route window.

    These values select a batch of routes based on the current hour, so that
    unattended hourly jobs always record a different slice of the route list.
    Any other ``start`` is returned unchanged together with ``end``.
    """
    if start in (400, 404, 900):
        batch = start // 100
        first = (batch * (now_hour + 1) + (start % 100)) % 101
        return first, (first + batch - 1) % 101
    return start, end


def screenshot_exists(folder: str, city: str, date: str, route_id: int, suffix: str) -> bool:
    """Check whether the screenshot of one route/app already exists."""
    return os.path.exists(screenshot_path(folder, city, date, route_id, suffix))


def screenshot_path(folder: str, city: str, date: str, route_id: int, suffix: str) -> str:
    """Build the canonical screenshot file path ``<city><date><id:03d><suffix>.png``."""
    return os.path.join(folder, f"{city}{date}{route_id:03d}{suffix}.png")
