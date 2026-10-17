"""Example 4 — build an HTML report from a synthetic result CSV.

No phone, no OCR engine and no config file are needed: this writes a small
result CSV in the same shape the analyser produces, then renders the report.

Run:  python examples/04_report.py
Then open  workspace/reports/demo/report_ZZ_NYC_0101.html
"""

import csv
import random
from pathlib import Path

from appautomation.report import write_report

HEADER = ["id", "date", "time", "dist", "trip", "toll", "surcharge", "surge", "price",
          "base", "minimum", "minute", "kilo", "booking", "rateB", "short", "medium",
          "long", "rateT", "rateD", "valid", "src", "dst"]

ROUTES = [
    ("Times Square", "JFK Airport"),
    ("Grand Central Terminal", "Brooklyn Bridge"),
    ("Wall Street", "Central Park"),
    ("Penn Station", "LaGuardia Airport"),
    ("Hudson Yards", "SoHo"),
    ("Columbus Circle", "Williamsburg"),
]

random.seed(7)  # keep the example reproducible
out_dir = Path("workspace/reports/demo")
out_dir.mkdir(parents=True, exist_ok=True)
csv_path = out_dir / "ZZ_NYC_0101.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=HEADER)
    writer.writeheader()
    for index, (src, dst) in enumerate(ROUTES, 1):
        distance = round(random.uniform(3.0, 26.0), 1)
        minutes = int(distance * random.uniform(2.0, 3.6))
        base = round(random.uniform(2.5, 4.5), 2)
        km_rate = round(random.uniform(1.1, 2.2), 2)
        min_rate = round(random.uniform(0.3, 0.8), 2)
        # Every fifth route simulates a failed capture (no price)
        failed = index % 5 == 0
        writer.writerow({
            "id": index, "date": "2026/10/17", "time": f"09:{index * 7:02d}",
            "dist": distance, "trip": minutes,
            "toll": "" if failed else round(random.uniform(0, 3.5), 2),
            "price": "" if failed else round(base + km_rate * distance + min_rate * minutes, 2),
            "base": base, "kilo": km_rate, "minute": min_rate,
            "booking": round(random.uniform(0.5, 2.0), 2),
            "src": src, "dst": dst,
        })

report = write_report([csv_path])
print(f"report: {report}")
