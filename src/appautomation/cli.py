"""Command line interface.

Examples::

    appautomation --phone phone_a --city BOLT_MEL --date 0000 --start 1 --end 10
    appautomation --phone phone_a --city MEL --date 0906 --start 1 --end 10 --analyse
"""

from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from datetime import datetime
from typing import List, Optional

from .config import load_config
from .naming import get_record_range
from .runner import RunParams, analyse, run, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appautomation",
        description="Record fare screenshots from Android ride-hailing apps and analyse them.")
    parser.add_argument("--config", help="path to config.yaml (default: $APPAUTOMATION_CONFIG or ./config.yaml)")
    parser.add_argument("--phone", required=True, help="phone alias defined in config.yaml")
    parser.add_argument("--city", required=True,
                        help="task / city, e.g. MEL, BOLT_MEL, GOOGLE_SYD, INDRIVE_PER, TIME_MEL")
    parser.add_argument("--date", required=True,
                        help="date label for file names, e.g. 0906 (MMDD); 0000 = today")
    parser.add_argument("--start", type=int, required=True, help="first route id to record")
    parser.add_argument("--end", type=int, required=True, help="last route id to record")
    parser.add_argument("--analyse", action="store_true",
                        help="analyse existing screenshots only (do not touch the phone)")
    parser.add_argument("--capture-only", action="store_true",
                        help="record screenshots but skip the OCR analysis")
    parser.add_argument("--partial", action="store_true",
                        help="only record the route ids listed under partial_routes in config.yaml")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    today = _date.today()
    date_label = f"{today.month:02d}{today.day:02d}" if args.date == "0000" else args.date
    start, end = get_record_range(args.start, args.end, datetime.now().hour)

    params = RunParams(
        config=config, phone=args.phone.lower(), task=args.city.upper(), date=date_label,
        start=start, end=end, partial=args.partial, capture_only=args.capture_only,
    )
    config.phone(params.phone)  # fail early on an unknown alias

    if args.analyse:
        setup_logging(params)
        analyse(params)
        sys.exit(0)
    run(params)


if __name__ == "__main__":
    main()
