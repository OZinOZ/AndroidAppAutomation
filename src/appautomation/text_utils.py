"""Helpers for turning raw OCR text into numbers."""

from __future__ import annotations

import re
from typing import Tuple

_GOOGLE_FULL = re.compile(r"^(.*? ?)(\dhr ?)?(\d+) ?min ?\((\d+.?\d?) ?km\).*$")
_GOOGLE_SMALL_1 = re.compile(r"^.*?(\d+).*min.*?(\d+\.?\d?).*km.*$")
_GOOGLE_SMALL_2 = re.compile(r"^(.*?)( \d+ )(.*?)min.*?(\d+\.?\d?).*km.*$")


def to_float(text: str) -> float:
    """Extract a float from ``text`` ignoring every non numeric character.

    >>> to_float("$12.50")
    12.5
    >>> to_float("n/a")
    0.0
    """
    cleaned = re.sub(r"[^0-9.]", "", text).strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def to_int(text: str) -> int:
    """Extract an int from ``text`` ignoring every non digit character."""
    cleaned = re.sub(r"[^0-9]", "", text).strip()
    try:
        return int(cleaned)
    except ValueError:
        return 0


def search_google_info(map_info: str) -> Tuple[float, int]:
    """Parse ``"1hr 5 min (23.4 km)"`` style text into ``(km, minutes)``.

    Returns ``(0.0, 0)`` when the text does not match.
    """
    match = _GOOGLE_FULL.match(" ".join(map_info.split()))
    if not match:
        return 0.0, 0
    minutes = to_int(match.group(3))
    if match.group(2):  # an "Xhr" part is present
        minutes += 60 * to_int(match.group(2))
    return to_float(match.group(4)), minutes


def search_google_small(map_info: str) -> Tuple[float, int]:
    """Looser fallback of :func:`search_google_info` for noisy OCR output."""
    text = " ".join(map_info.split())
    match = _GOOGLE_SMALL_1.match(text)
    if match:
        return to_float(match.group(2)), to_int(match.group(1))
    match = _GOOGLE_SMALL_2.match(text)
    if match:
        return to_float(match.group(4)), to_int(match.group(2))
    return 0.0, 0


def search_price(text: str, pattern: str, group: int) -> float:
    """Return the price captured by ``pattern`` (``group`` index) or ``0.0``.

    OCR frequently drops the decimal point (``"1250"`` instead of ``"12.50"``);
    in that case the last two digits are treated as cents.
    """
    match = re.match(pattern, text)
    if not match:
        return 0.0
    value = match.group(group)
    if "." not in value:
        value = value[:-2] + "." + value[-2:]
    return to_float(value)
