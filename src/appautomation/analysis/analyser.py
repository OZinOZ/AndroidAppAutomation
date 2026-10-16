"""Batch analysis: screenshots of a run -> one result CSV."""

from __future__ import annotations

import csv
import logging
import os
import re
from pathlib import Path
from typing import Dict, List

from ..constants import RESULT_FIELDS
from ..naming import screenshot_path
from ..routes import read_routes
from .parser import ScreenshotParser

logger = logging.getLogger(__name__)

#: Screenshot suffixes consumed per route, in parse order.
FILE_IDS = ("B", "BI", "G")


def clean_address(address: str) -> str:
    """Lower-case an address and drop punctuation."""
    return re.sub(r"[^A-Za-z0-9 ]", "", str(address).lower())


class ScreenshotAnalyser:
    """Analyse every route of one run (one city, one date, one phone).

    Args:
        parser: Configured :class:`ScreenshotParser`.
        work_base: Workspace root containing ``routes/``.
        city: Route file name (``NYC`` for ``routes/NYC.csv``).
        date: Date label used in screenshot file names (e.g. ``0906``).
        screenshot_dir: Folder with the screenshots; the CSV is written here too.
        label: Name used in log messages (usually the phone alias).
    """

    def __init__(self, parser: ScreenshotParser, work_base: Path, city: str,
                 date: str, screenshot_dir: str, label: str = ""):
        self.parser = parser
        self.work_base = work_base
        self.city = city
        self.date = date
        self.dir = screenshot_dir
        self.label = label
        self.csv_path = os.path.join(screenshot_dir, f"ZZ_{city}_{date}.csv")

    def run(self) -> str:
        """Parse all routes and write the result CSV. Returns the CSV path."""
        logger.info("%s analyse routes start", self.label.upper())
        routes = read_routes(self.work_base, self.city)

        with open(self.csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=RESULT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for route_id, route in enumerate(routes, 1):
                row = self.analyse_route(route_id, route)
                writer.writerow(row)
                if "time" in row:
                    print("Bolt:", row)

        logger.info("%s analyse finish, result: %s", self.label.upper(), self.csv_path)
        return self.csv_path

    def analyse_route(self, route_id: int, route: Dict[str, object]) -> Dict[str, object]:
        """Parse all screenshots that exist for one route into a result row."""
        row: Dict[str, object] = {
            "id": route_id, "src": clean_address(route["src"]),
            "dst": clean_address(route["dst"]), "surge": "", "valid": "",
        }
        for file_id in FILE_IDS:
            path = screenshot_path(self.dir, self.city, self.date, route_id, file_id)
            if os.path.exists(path):
                self.parser.parse(file_id, path, row)
            elif file_id == "G":
                self._promote_alternative_google(route_id, path, row)
        return row

    def _promote_alternative_google(self, route_id: int, target: str, row: Dict[str, object]) -> None:
        """If only ``G0`` / ``G1`` exist (no direct ``G``), rename the first one to ``G``."""
        for i in range(2):
            alt = screenshot_path(self.dir, self.city, self.date, route_id, f"G{i}")
            if os.path.exists(alt):
                os.rename(alt, target)
                self.parser.parse("G", target, row)
                return


def list_missing(directory: str, city: str, date: str, route_ids: List[int],
                 suffixes: List[str]) -> List[int]:
    """Return the route ids lacking at least one of the ``suffixes`` screenshots."""
    return [
        rid for rid in route_ids
        if not all(os.path.exists(screenshot_path(directory, city, date, rid, s)) for s in suffixes)
    ]
