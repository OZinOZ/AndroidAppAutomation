"""HTML report generation: result CSV(s) → one self-contained HTML page.

The report is deliberately dependency-free (no JS framework, no chart library):
inline CSS and inline SVG are generated from the data, so the file can be
mailed, committed as an artifact, or opened offline.

Typical use::

    appautomation --report screenshots/0906_NYC_phone_a/ZZ_NYC_0906.csv
    appautomation --report run_a/ZZ_NYC_0906.csv run_b/ZZ_NYC_0906.csv -o out.html
"""

from __future__ import annotations

import csv
import html
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

#: Columns treated as numbers; empty or unparsable values count as missing.
NUMERIC_FIELDS = (
    "price", "dist", "trip", "toll", "surcharge", "surge", "base",
    "minimum", "minute", "kilo", "booking",
)

#: Fee columns shown in the breakdown section (order matters for display).
FEE_FIELDS = ("base", "booking", "toll", "surcharge", "minimum", "kilo", "minute")


@dataclass
class Summary:
    """Aggregated statistics for one result CSV."""

    label: str
    routes: int = 0
    priced: int = 0
    priced_share: float = 0.0
    mean_price: float = 0.0
    median_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    mean_dist: float = 0.0
    mean_trip: float = 0.0
    missing: Dict[str, int] = field(default_factory=dict)
    fees: Dict[str, float] = field(default_factory=dict)


def _to_float(value: object) -> Optional[float]:
    """Parse a CSV cell into a float; ``None`` when empty/unparsable/zero-price."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_rows(path: Path) -> List[Dict[str, object]]:
    """Read one result CSV (written by :class:`analysis.analyser.ScreenshotAnalyser`)."""
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def summarise(label: str, rows: Sequence[Dict[str, object]]) -> Summary:
    """Compute the KPI values shown on the report cards."""
    prices = [p for p in (_to_float(r.get("price")) for r in rows) if p]
    dists = [d for d in (_to_float(r.get("dist")) for r in rows) if d]
    trips = [t for t in (_to_float(r.get("trip")) for r in rows) if t]

    summary = Summary(
        label=label,
        routes=len(rows),
        priced=len(prices),
        priced_share=len(prices) / len(rows) if rows else 0.0,
        mean_price=statistics.fmean(prices) if prices else 0.0,
        median_price=statistics.median(prices) if prices else 0.0,
        min_price=min(prices) if prices else 0.0,
        max_price=max(prices) if prices else 0.0,
        mean_dist=statistics.fmean(dists) if dists else 0.0,
        mean_trip=statistics.fmean(trips) if trips else 0.0,
    )

    for column in NUMERIC_FIELDS:
        missing = sum(1 for r in rows if _to_float(r.get(column)) is None)
        if missing:
            summary.missing[column] = missing

    for fee in FEE_FIELDS:
        values = [v for v in (_to_float(r.get(fee)) for r in rows) if v]
        if values:
            summary.fees[fee] = statistics.fmean(values)

    return summary


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _svg_bars(items: Sequence[Tuple[str, float]], width: int = 620,
              bar_height: int = 18, gap: int = 7) -> str:
    """Render a horizontal bar chart as inline SVG (no JS)."""
    if not items:
        return '<p class="muted">No priced routes to plot.</p>'

    label_width = 150
    value_width = 70
    chart_width = width - label_width - value_width
    peak = max(value for _, value in items) or 1.0
    height = len(items) * (bar_height + gap) + gap

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" '
             f'role="img" aria-label="Price per route" class="chart">']
    for index, (label, value) in enumerate(items):
        y = gap + index * (bar_height + gap)
        length = max(2.0, chart_width * value / peak)
        parts.append(
            f'<text x="0" y="{y + bar_height - 4}" class="bar-label">{_esc(label)}</text>'
            f'<rect x="{label_width}" y="{y}" width="{length:.1f}" height="{bar_height}" '
            f'rx="3" class="bar"></rect>'
            f'<text x="{label_width + length + 8:.1f}" y="{y + bar_height - 4}" '
            f'class="bar-value">${value:,.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _cards(summary: Summary) -> str:
    cards = [
        ("Routes", f"{summary.routes}", "recorded in this result file"),
        ("With price", f"{summary.priced}", f"{summary.priced_share:.1%} of routes"),
        ("Mean fare", f"${summary.mean_price:,.2f}", f"median ${summary.median_price:,.2f}"),
        ("Range", f"${summary.min_price:,.2f} – ${summary.max_price:,.2f}",
         f"avg {summary.mean_dist:.1f} km / {summary.mean_trip:.0f} min"),
    ]
    return "".join(
        f'<div class="card"><div class="card-label">{_esc(title)}</div>'
        f'<div class="card-value">{_esc(value)}</div>'
        f'<div class="card-note">{_esc(note)}</div></div>'
        for title, value, note in cards
    )


def _route_rows(rows: Sequence[Dict[str, object]]) -> str:
    body = []
    for row in rows:
        price = _to_float(row.get("price"))
        dist = _to_float(row.get("dist"))
        trip = _to_float(row.get("trip"))
        body.append(
            "<tr>"
            f"<td>{_esc(row.get('id'))}</td>"
            f"<td>{_esc(row.get('src'))}</td>"
            f"<td>{_esc(row.get('dst'))}</td>"
            f"<td class=\"num\">{('$%.2f' % price) if price else '—'}</td>"
            f"<td class=\"num\">{(('%.1f km' % dist) if dist else '—')}</td>"
            f"<td class=\"num\">{(('%d min' % trip) if trip else '—')}</td>"
            f"<td class=\"num\">{_esc(row.get('date'))} {_esc(row.get('time'))}</td>"
            "</tr>"
        )
    return "".join(body)


def _fees_table(fees: Dict[str, float]) -> str:
    if not fees:
        return '<p class="muted">No fare breakdown values in this data set.</p>'
    rows = "".join(
        f'<tr><td>{_esc(label)}</td><td class="num">${value:,.2f}</td></tr>'
        for label, value in sorted(fees.items(), key=lambda kv: -kv[1])
    )
    return f'<table class="plain"><thead><tr><th>Fee component</th>' \
           f'<th class="num">Mean value</th></tr></thead><tbody>{rows}</tbody></table>'


def _missing_table(missing: Dict[str, int], total: int) -> str:
    if not missing:
        return '<p class="ok">Every numeric column is populated for all routes.</p>'
    rows = "".join(
        f'<tr><td>{_esc(column)}</td><td class="num">{count}</td>'
        f'<td class="num">{count / total:.0%}</td></tr>'
        for column, count in sorted(missing.items(), key=lambda kv: -kv[1])
    )
    return '<table class="plain"><thead><tr><th>Column</th>' \
           f'<th class="num">Missing</th><th class="num">Share</th></tr></thead>' \
           f'<tbody>{rows}</tbody></table>'


def _comparison_table(summaries: Sequence[Summary]) -> str:
    if len(summaries) < 2:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(s.label)}</td><td class=\"num\">{s.routes}</td>"
        f"<td class=\"num\">{s.priced_share:.0%}</td>"
        f"<td class=\"num\">${s.mean_price:,.2f}</td>"
        f"<td class=\"num\">${s.median_price:,.2f}</td>"
        f"<td class=\"num\">{s.mean_dist:.1f} km</td></tr>"
        for s in summaries
    )
    return (
        "<h2>Run comparison</h2>"
        '<table class="plain"><thead><tr><th>Result file</th><th class="num">Routes</th>'
        '<th class="num">Priced</th><th class="num">Mean</th><th class="num">Median</th>'
        f'<th class="num">Distance</th></tr></thead><tbody>{rows}</tbody></table>'
    )


CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1a1d23;--muted:#6b7280;--line:#e5e7eb;
--accent:#2563eb;--ok:#0f766e;--warn:#b45309}
*{box-sizing:border-box}
body{margin:0;padding:32px;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:17px;margin:34px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--muted);font-size:13px;margin-bottom:24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card-label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.card-value{font-size:22px;font-weight:600;margin:6px 0 2px}
.card-note{color:var(--muted);font-size:12px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}
tbody tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
table.plain{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.bar{fill:var(--accent)}
.bar-label{font-size:12px;fill:#374151}
.bar-value{font-size:12px;fill:#111827;font-weight:600}
.chart{display:block}
.muted{color:var(--muted)}
.ok{color:var(--ok)}
footer{margin-top:36px;color:var(--muted);font-size:12px}
"""


def render_report(datasets: Sequence[Tuple[str, Sequence[Dict[str, object]]]],
                  title: str = "Fare capture report") -> str:
    """Render the full HTML page for one or more labelled datasets."""
    summaries = [summarise(label, rows) for label, rows in datasets]
    primary_label, primary_rows = datasets[0] if datasets else ("", [])

    bars = []
    for row in primary_rows:
        price = _to_float(row.get("price"))
        if price:
            bars.append((f"#{_esc(row.get('id'))}", price))

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    comparison = _comparison_table(summaries)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<h1>{_esc(title)}</h1>
<p class="sub">{_esc(primary_label)} · generated {generated} by appautomation</p>

<div class="cards">{_cards(summaries[0])}</div>

<h2>Price by route</h2>
<div class="panel">{_svg_bars(bars)}</div>

<h2>Fare breakdown (mean)</h2>
{_fees_table(summaries[0].fees)}

<h2>Data quality</h2>
{_missing_table(summaries[0].missing, max(1, summaries[0].routes))}

{comparison}

<h2>Routes</h2>
<table>
<thead><tr><th>id</th><th>pickup</th><th>drop-off</th><th class="num">price</th>
<th class="num">distance</th><th class="num">duration</th><th class="num">captured</th></tr></thead>
<tbody>{_route_rows(primary_rows)}</tbody>
</table>

<footer>Generated from {len(datasets)} result file(s) ·
{summaries[0].routes} route(s). Values are OCR-extracted; treat them as observations.</footer>
</body>
</html>
"""


def write_report(paths: Sequence[Path], output: Optional[str] = None,
                 title: Optional[str] = None) -> Path:
    """Build a report from one or more result CSVs and write it to ``output``.

    Default output: ``<first csv dir>/report_<first csv stem>.html``.
    """
    if not paths:
        raise ValueError("At least one result CSV is required")

    datasets: List[Tuple[str, Sequence[Dict[str, object]]]] = []
    for path in paths:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Result CSV not found: {path}")
        label = path.name if str(path.parent) in ("", ".") else f"{path.parent.name}/{path.name}"
        datasets.append((label, load_rows(path)))

    csv_path = Path(paths[0])
    out = Path(output) if output else csv_path.with_name(f"report_{csv_path.stem}.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(datasets, title or f"Fare capture report — {csv_path.stem}"),
                   encoding="utf-8")
    return out
