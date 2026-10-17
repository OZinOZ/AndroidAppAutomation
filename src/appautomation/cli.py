"""Command line interface.

Capture::

    appautomation --phone phone_a --city BOLT_NYC --date 0000 --start 1 --end 10
    appautomation --phone phone_a --city NYC --date 0906 --start 1 --end 10 --analyse

Report (no phone, config or route range needed)::

    appautomation --report workspace/screenshots/0906_NYC_phone_a/ZZ_NYC_0906.csv
    appautomation --report run_a/ZZ_NYC_0906.csv run_b/ZZ_NYC_0906.csv -o compare.html
"""

from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import load_config
from .naming import get_record_range
from .runner import RunParams, analyse, run, setup_logging

#: Arguments required for a capture / analyse run (but not for --report).
RUN_ARGUMENTS = ("phone", "city", "date", "start", "end")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appautomation",
        description="Record fare screenshots from Android ride-hailing apps and analyse them.")
    parser.add_argument("--config", help="path to config.yaml (default: $APPAUTOMATION_CONFIG or ./config.yaml)")
    parser.add_argument("--phone", help="phone alias defined in config.yaml")
    parser.add_argument("--city",
                        help="task / city, e.g. NYC, BOLT_NYC, GOOGLE_LAX, INDRIVE_HOU, TIME_NYC")
    parser.add_argument("--date",
                        help="date label for file names, e.g. 0906 (MMDD); 0000 = today")
    parser.add_argument("--start", type=int, help="first route id to record")
    parser.add_argument("--end", type=int, help="last route id to record")
    parser.add_argument("--analyse", action="store_true",
                        help="analyse existing screenshots only (do not touch the phone)")
    parser.add_argument("--capture-only", action="store_true",
                        help="record screenshots but skip the OCR analysis")
    parser.add_argument("--partial", action="store_true",
                        help="only record the route ids listed under partial_routes in config.yaml")
    parser.add_argument("--report", nargs="+", metavar="CSV",
                        help="build an HTML report from one or more result CSVs and exit")
    parser.add_argument("-o", "--output", metavar="PATH",
                        help="output path for --report (default: report_<csv stem>.html next to the CSV)")
    return parser


def _missing_run_arguments(args: argparse.Namespace) -> List[str]:
    return [name for name in RUN_ARGUMENTS if getattr(args, name) is None]


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Report mode: no phone, config or route range involved
    if args.report:
        from .report import write_report

        out = write_report([Path(p) for p in args.report], args.output)
        print(f"Report written to {out}")
        return

    missing = _missing_run_arguments(args)
    if missing:
        parser.error("the following arguments are required unless --report is used: "
                     + ", ".join(f"--{name}" for name in missing))

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
