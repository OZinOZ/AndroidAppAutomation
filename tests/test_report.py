"""Tests for the HTML report generator (no device, no OCR, no browser)."""

import csv

import pytest

from appautomation.cli import main
from appautomation.report import load_rows, render_report, summarise, write_report

HEADER = ["id", "date", "time", "dist", "trip", "toll", "surcharge", "surge", "price",
          "base", "minimum", "minute", "kilo", "booking", "rateB", "short", "medium",
          "long", "rateT", "rateD", "valid", "src", "dst"]


def _row(route_id, price="", dist="", trip="", toll="", base="", src="Times Square",
         dst="JFK Airport"):
    row = {field: "" for field in HEADER}
    row.update({"id": str(route_id), "price": price, "dist": dist, "trip": trip,
                "toll": toll, "base": base, "date": "2026/10/17", "time": "09:15",
                "src": src, "dst": dst})
    return row


def write_csv(tmp_path, rows, name="ZZ_NYC_0906.csv"):
    path = tmp_path / name
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_summarise_price_statistics():
    rows = [_row(1, price="10.00", dist="5.0", trip="12", toll="1.50"),
            _row(2, price="20.00", dist="9.0", trip="20"),
            _row(3, price="")]  # failed capture: no price

    summary = summarise("run", rows)

    assert summary.routes == 3
    assert summary.priced == 2
    assert summary.priced_share == pytest.approx(2 / 3)
    assert summary.mean_price == pytest.approx(15.0)
    assert summary.median_price == pytest.approx(15.0)
    assert summary.min_price == pytest.approx(10.0)
    assert summary.max_price == pytest.approx(20.0)
    assert summary.mean_dist == pytest.approx(7.0)
    assert summary.fees["toll"] == pytest.approx(1.5)
    assert summary.missing["price"] == 1


def test_load_rows_reads_written_csv(tmp_path):
    path = write_csv(tmp_path, [_row(1, price="12.30")])
    rows = load_rows(path)
    assert len(rows) == 1
    assert rows[0]["price"] == "12.30"


def test_render_escapes_addresses_and_shows_values():
    rows = [_row(1, price="18.40", src="<script>alert(1)</script>", dst="JFK & Co")]
    page = render_report([("run", rows)])

    assert "&lt;script&gt;" in page
    assert "<script>alert(1)</script>" not in page
    assert "JFK &amp; Co" in page
    assert "$18.40" in page
    assert "Fare breakdown" in page


def test_render_multiple_datasets_adds_comparison():
    first = [_row(1, price="10.00")]
    second = [_row(1, price="14.00")]
    page = render_report([("run_a/ZZ_NYC_0906.csv", first), ("run_b/ZZ_NYC_0906.csv", second)])

    assert "Run comparison" in page
    assert "run_a/ZZ_NYC_0906.csv" in page
    assert "$14.00" in page


def test_render_empty_dataset_does_not_crash():
    page = render_report([("empty", [])])
    assert "No priced routes to plot." in page
    assert "0" in page


def test_write_report_default_output_next_to_csv(tmp_path):
    path = write_csv(tmp_path, [_row(1, price="9.99")])
    out = write_report([path])

    assert out == path.with_name("report_ZZ_NYC_0906.html")
    assert out.is_file()
    assert "9.99" in out.read_text(encoding="utf-8")


def test_write_report_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        write_report([tmp_path / "nope.csv"])


def test_cli_report_mode(tmp_path, capsys):
    path = write_csv(tmp_path, [_row(1, price="21.50")], name="ZZ_NYC_0906.csv")
    out = tmp_path / "compare.html"

    main(["--report", str(path), "-o", str(out)])

    assert out.is_file()
    assert "Report written" in capsys.readouterr().out
