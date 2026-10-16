"""Static lookup tables shared across the package."""

from __future__ import annotations

from typing import Dict, List, Tuple

#: Hours between the timestamps stored in scheduled route files and local time.
TIME_DIFFERENCE = 2

#: Abort a run after this many routes failed in a row (non-scheduled mode).
MAX_FAIL_THRESHOLD = 3

# --------------------------------------------------------------------------- #
# Cities
# --------------------------------------------------------------------------- #
#: Short city code -> full city name (used to build search addresses).
CITY_NAMES: Dict[str, str] = {
    "NYC": "New York", "LAX": "Los Angeles", "CHI": "Chicago",
    "SFO": "San Francisco", "HOU": "Houston", "MIA": "Miami",
}
#: City code -> US state abbreviation.
CITY_STATES: Dict[str, str] = {
    "NYC": "NY", "LAX": "CA", "CHI": "IL", "SFO": "CA", "HOU": "TX", "MIA": "FL",
}
#: City code -> country name, for cities outside the home country.
#: All supported cities are domestic; kept for cross-border support (see
#: ``address_adapt`` in naming.py).
CITY_COUNTRIES: Dict[str, str] = {}

#: Service suffixes that may follow a city code, e.g. ``MIA_DROPOFF``.
SERVICES: Tuple[str, ...] = ("MAX", "PICKUP", "DROPOFF", "DELIVER", "XLMAX", "TRAVEL", "SELECT")
#: App prefixes that may precede a city code, e.g. ``BOLT_NYC``.
PREFIXES: Tuple[str, ...] = ("BOLT", "INDRIVE", "GOOGLE")

# --------------------------------------------------------------------------- #
# Which apps are driven for which task name
# --------------------------------------------------------------------------- #
#: Task key (first or last ``_`` separated token of ``--city``) -> apps, in order.
TASK_APPS: Dict[str, List[str]] = {
    "DEFAULT": ["bolt", "google"],
    "BOLT": ["bolt", "google"],
    "INDRIVE": ["indrive"],
    "GOOGLE": ["google"],
    "TIME": ["bolt"],
}

#: Task keys for which OCR analysis is skipped after capturing.
NO_ANALYSIS_TASKS = {"TIME", "INDRIVE"}

# --------------------------------------------------------------------------- #
# Screenshot regions of interest
# --------------------------------------------------------------------------- #
#: ``profile -> scope -> (top, bottom, left, right)`` in screen pixels.
#: The default profile was tuned on a 720x1560 screen. Add your own profile
#: for other resolutions and reference it from ``config.yaml``.
SCREEN_PROFILES: Dict[str, Dict[str, Tuple[int, int, int, int]]] = {
    "hd720": {
        "B": (875, 1070, 500, 690),     # Bolt fare estimate
        "BI": (650, 1380, 40, 650),     # Bolt fare breakdown
        "G": (1320, 1450, 10, 710),     # Google Maps route summary (compact)
        "G2": (1020, 1370, 10, 710),    # Google Maps route summary (expanded)
    },
}

#: Normalised fee name -> labels that may appear on the fare breakdown screen.
CHARGE_MAP: Dict[str, List[str]] = {
    "toll": ["Estimated Tolls", "Estimated tolls", "Highway Fee"],
    "surcharge": ["CTP Fee", "Airport Fee", "Estimated surcharges", "Holiday Surcharge"],
    "base": ["Base fare", "Start"],
    "rateB": ["Base Fare"],
    "kilo": ["per kilometre", "Per km"],
    "minute": ["Per Minute", "Per min"],
    "booking": ["Booking Fee", "Convenience Fee", "Booking fee"],
    "rateT": ["Time Rate"],
    "rateD": ["Distance Rate"],
    "minimum": ["Minimum fare", "Minimum Fare", "Minimum price"],
    "long": ["Above 20 km"],
    "short": ["0-12 km", "12 km", "0 - 12 km"],
    "medium": ["12 - 20 km", "20 km"],
}

#: Column order of the result CSV written by the analyser.
RESULT_FIELDS: List[str] = [
    "id", "date", "time", "dist", "trip", "toll", "surcharge", "surge", "price",
    "base", "minimum", "minute", "kilo", "booking",
    "rateB", "short", "medium", "long", "rateT", "rateD",
    "valid", "src", "dst",
]
