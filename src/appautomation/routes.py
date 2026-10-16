"""Route (pickup / drop-off) list loading."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

Route = Dict[str, object]


def routes_file(work_base: Path, name: str) -> Path:
    """Path of ``<work_base>/routes/<name>.csv``."""
    return Path(work_base) / "routes" / f"{name}.csv"


def read_routes(work_base: Path, name: str) -> List[Route]:
    """Load all routes. CSV columns: ``id,src,dst`` (+ ``hour,minute`` for TIME tasks)."""
    return pd.read_csv(routes_file(work_base, name)).to_dict("records")


def select_routes(routes: Iterable[Route], start: int, end: int,
                  partial: bool = False, partial_ids: Iterable[int] = ()) -> List[Route]:
    """Keep routes whose ``id`` is in ``[start, end]``.

    With ``partial`` only ids listed in ``partial_ids`` survive.
    """
    wanted = set(partial_ids)
    return [
        route for route in routes
        if start <= int(route["id"]) <= end and (not partial or int(route["id"]) in wanted)
    ]
