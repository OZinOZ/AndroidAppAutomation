# Test Plan — AppAutomation

Version 1.0 · 2026-10-17

Scope: how the tool is verified at each level, what is already automated,
and the acceptance thresholds for a release. Requirements: [`REQUIREMENTS.md`](REQUIREMENTS.md);
design: [`DESIGN.md`](DESIGN.md).

---

## 1. Test levels

| Level | Target | Environment | Automation |
|-------|--------|-------------|------------|
| L1 Unit | Pure logic: task names, address expansion, price/duration regex, route selection | No device, no OCR | ✅ pytest in CI |
| L2 Component | Driver flows against a fake device object; parser against synthetic screenshots | No real phone | ⬜ planned (see §4) |
| L3 Device integration | Real app, real phone: driver reaches every screen and produces required suffixes | USB device, apps installed | 🔲 manual checklist (§5) |
| L4 System / E2E | Full run: capture → analysis → CSV; failure paths; notifications | Full setup | 🔲 scripted scenario (§6) |
| L5 OCR accuracy | Extraction correctness against a labelled calibration set | OCR engine installed | 🔲 benchmark (§7) |

## 2. L1 — Unit tests (implemented)

CI runs `pytest` on every push (`.github/workflows/ci.yml`, Python 3.9/3.12).

| Test | Verifies |
|------|----------|
| `test_to_float_and_int` | `to_float("$12.50") == 12.5`, non-numeric → 0.0, `to_int("20 km") == 20` (FR-3.2) |
| `test_google_info_with_hours` | `1hr 5 min (23.4 km)` → `(23.4, 65)` (FR-3.2) |
| `test_google_info_no_match` | No match → `(0.0, 0)` without raising (NFR-2) |
| `test_google_small_fallback` | Loose pattern `12 min away 5.2 km` fallback (FR-3.2) |
| `test_search_price_discount_group` | Discounted price picked from two-price text (FR-3.2) |
| `test_search_price_missing_decimal_point` | `"$2130"` → `21.3` OCR-glitch tolerance (NFR-2) |
| `test_task_names` | `BOLT_MEL` / `SUN_DROPOFF` / `MEL` / `TIME_MEL` name parsing (FR-5, D1) |
| `test_address_adapt` | State/city expansion incl. non-AU country suffix (FR-1.3) |
| `test_record_range` | Magic start values `400/404/900` hourly batching (FR-5.2) |

Threshold: 100% pass; lint (`ruff E9+F`) must be clean in the same run.

## 3. Regression strategy

* **Logic** — covered by L1; new helpers land together with a test.
* **Screenshots/OCR** — golden-set regression (§7): a small directory of
  calibrated screenshots must keep producing identical `price/dist/trip`
  after parser or profile changes.
* **Driver flows** — UI changes in the target apps are external; drivers are
  re-verified with the L3 checklist after any app update.

## 4. L2 — Component tests (planned)

1. **Driver flows with a fake device** — stub `Device`/`UiResource` calls and
   assert the interaction sequence (launch → dialogs → inputs → screenshots
   with expected suffixes) and that `False` vs `AppNotReadyError` propagate
   per the contract (D2, D8).
2. **Runner policies** — retry-once, `MAX_FAIL_THRESHOLD` abort, incomplete
   route redo, `TIME_*` scheduling selection — with a scripted route/device
   fake.
3. **Parser on synthetic images** — generate PNGs with known text at known
   crop positions (as `examples/02_synthetic_analysis.py` does) and assert
   row fields incl. `G0` promotion (FR-3.4) and fee range brackets.

## 5. L3 — Manual device checklist (per driver)

Preconditions: device unlocked, app logged in, `adb devices` shows serial.

For **Bolt** (`BOLT_<CITY>`): [ ] app relaunches cleanly (stop/start)
[ ] pickup entered & suggestion accepted [ ] destination entered
[ ] `confirm_button`/`closeButtonImage` dialogs handled when present
[ ] `B` shows ride options with price [ ] `BI` shows fare breakdown.
For **inDrive** (`INDRIVE_<CITY>`): [ ] location dialog answered "NO"
[ ] both addresses accepted [ ] `IN` shows offer screen.
For **Google Maps** (`GOOGLE_<CITY>`): [ ] search → directions → start point
[ ] `G` (or promoted `G0`) shows distance/duration [ ] alternative routes captured.
Negative: logged-out app aborts run with `FAIL to start APP!!` notification;
USB disconnected mid-run retries once then exits non-zero.

## 6. L4 — System scenarios

| # | Scenario | Expected |
|---|----------|----------|
| S1 | `BOLT_MEL` routes 1–20, capture+analyse | ≥ 95% complete screenshot sets; CSV has valid `price` for ≥ 95% of rows; success e-mail |
| S2 | `--analyse` re-run on a second machine from the screenshots dir alone | Identical CSV values (FR acceptance #4) |
| S3 | `--partial` with 3 ids | Only those ids captured and analysed |
| S4 | `TIME_MEL` scheduled file | Routes recorded within their minute slots; no analysis CSV |
| S5 | All apps logged out | Abort ≤ 3 routes, failure e-mail, exit code 1, phone screen off |
| S6 | `--capture-only` on machine without OCR | Capture completes; no analysis crash (FR-3.6) |

## 7. L5 — OCR accuracy benchmark

* Build a calibration set: ≥ 50 screenshots per suffix, labelled by hand
  (true price / fees / distance / duration).
* Metrics per field: extraction accuracy (exact match for fees, ± tolerance
  for OCR-fuzzy digits), parsed-value error rate.
* Release thresholds: `price` ≥ 98%, `dist`/`trip` ≥ 95%, breakdown fees
  ≥ 90% on the calibration set; regressions vs previous release block release.

## 8. CI

`.github/workflows/ci.yml`: push/PR to `main` → Python 3.9 & 3.12 matrix →
`pip install -e ".[dev]"` → `ruff check --select E9,F` → `pytest -v`.
L2/L5 join CI once implemented (they remain device-free).
