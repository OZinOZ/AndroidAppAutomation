# Requirements Specification — AppAutomation

Version 1.0 · 2026-10-17 · Status: implemented (v2)

This document specifies *what* the tool does and *how well* it must do it.
*How* it is built is covered in [`DESIGN.md`](DESIGN.md); quality assurance in
[`TEST_PLAN.md`](TEST_PLAN.md); future work in [`MULTI_DEVICE_PLAN.md`](MULTI_DEVICE_PLAN.md).

---

## 1. Purpose

Automate Android ride-hailing apps (Bolt, inDrive) and Google Maps on real
phones to **continuously observe fares**: for a list of routes, drive each
app's UI, screenshot the fare screens, and extract structured price, fee,
distance and duration data with OCR.

Primary use case: longitudinal fare monitoring (thousands of route × app ×
time observations) for analysis and comparison across apps, cities and dates.

## 2. Glossary

| Term | Meaning |
|------|---------|
| Route | One pickup → drop-off pair with a numeric id, stored in a city CSV |
| Task | `[APP_]CITY[_SERVICE]` name, e.g. `BOLT_NYC`, `TIME_NYC` |
| Driver | Per-app class that automates one app and produces screenshots |
| Suffix | Screenshot-type code (`B`, `BI`, `IN`, `G`) linking a PNG to OCR regions |
| Profile | Named set of pixel crop regions for one screen resolution |
| Run | One invocation of the CLI for one phone, task, date and route range |

## 3. User stories

* As a fare analyst, I want to record 100+ routes across several apps
  unattended, so that data collection does not need a person at the desk.
* As an analyst, I want distance/duration from Google Maps attached to every
  route, so that prices can be normalised per km/minute.
* As an operator, I want failures retried and, if persistent, to abort with a
  notification, so that a broken app does not silently waste hours.
* As an operator, I want analysis to run without a phone, so that capture and
  OCR can be decoupled (e.g. laptops without ADB can do OCR).
* As a developer, I want to add a new app or phone by touching one file and
  one config entry, so that the tool follows the apps it monitors.

## 4. Functional requirements

### FR-1 Route management
* FR-1.1 Load routes from `<work_base>/routes/<CITY>.csv` with columns `id,src,dst`.
* FR-1.2 Select an inclusive route range `--start/--end`; with `--partial`,
  restrict to configured route ids (`partial_routes`).
* FR-1.3 Expand short addresses with state / city / country based on the city
  code before entering them into app search (e.g. `Fed Sq` + `NYC` →
  `NY,Fed Sq,New York`).
* FR-1.4 `TIME_*` tasks read per-route `hour,minute` columns and record each
  route at its scheduled time.

### FR-2 Capture
* FR-2.1 For each selected route, drive every app mapped to the task (order
  defined by `TASK_APPS`), launch the app (stop → start) and enter pickup and
  destination through the app's UI.
* FR-2.2 Save screenshots as `<CITY><DATE><ID:03d><SUFFIX>.png` under
  `<work_base>/screenshots/[time/]<DATE>_<CITY>_<PHONE>/`.
* FR-2.3 Retry a failed app once; abort the run after `MAX_FAIL_THRESHOLD`
  (3) consecutive failed routes.
* FR-2.4 After the pass, re-run routes missing at least one required suffix
  screenshot (`required_suffixes` of the task's apps).
* FR-2.5 Wake and unlock the device (swipe, no PIN) before recording; reset
  uiautomator and turn the screen off after the run.
* FR-2.6 Keep request patterns human-like: randomised inter-route pauses.

### FR-3 Analysis
* FR-3.1 Crop each screenshot by the device's screen profile and run one OCR
  engine (EasyOCR preferred, then PaddleOCR, then Tesseract; `auto` = first
  installed).
* FR-3.2 Extract: fare estimate price (discount-aware), fee breakdown items
  (base, per-km, per-minute, booking, toll, surcharge, minimum, distance
  brackets), Google Maps distance (km) and duration (min).
* FR-3.3 Write one result CSV per run, `ZZ_<CITY>_<DATE>.csv`, with the fixed
  column set `RESULT_FIELDS`, joined with cleaned `src`/`dst`.
* FR-3.4 If no direct `G` screenshot exists, promote the first alternative
  (`G0`/`G1`) before parsing.
* FR-3.5 Tasks in `NO_ANALYSIS_TASKS` (`TIME`, `INDRIVE`) capture screenshots
  only.
* FR-3.6 `--analyse` runs OCR only, without touching a phone; on machines
  without any OCR engine, capture-only mode still works.

### FR-4 Configuration & credentials
* FR-4.1 All machine-specific values (serials, e-mail addresses, tool paths)
  live in `config.yaml`, resolved via `--config` → `$APPAUTOMATION_CONFIG` →
  `./config.yaml`; never committed.
* FR-4.2 Phones are addressed by alias (`phones.<alias>.serial`, optional
  screen `profile`); unknown alias is a hard, early error.
* FR-4.3 Optional Gmail notifications on run end (success or failure), driven
  by an `email:` config block; without it nothing is sent.

### FR-5 Command line
* FR-5.1 `appautomation --phone P --city T --date D --start N --end M
  [--analyse] [--capture-only] [--partial] [--config PATH]`.
* FR-5.2 `--date 0000` = today as `MMDD`; special start values `400/404/900`
  select an hourly route batch for unattended cron-style use.

## 5. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Runs on Python ≥ 3.9, Windows/macOS/Linux; heavy OCR deps are optional extras |
| NFR-2 | Unattended stability: single bad route never aborts the run; aborts are notified |
| NFR-3 | Extensibility: new app = one driver file + registry entry + constants entry |
| NFR-4 | Secrets never in the repository; git-ignored `config.yaml`, `credentials.json`, `token.json` |
| NFR-5 | All third-party automation is user-visible UI automation on a real device; no private API use (see README legal note) |
| NFR-6 | Lint-clean (ruff E9+F) and unit-tested in CI on every push |

## 6. Out of scope (v2)

* Multi-device parallel orchestration (planned — see `MULTI_DEVICE_PLAN.md`)
* Rooted/emulated devices, GPS spoofing, service-level API access
* iOS devices
* Web dashboard / live monitoring UI

## 7. Acceptance criteria (v2)

1. `pip install -e ".[dev]" && pytest` passes with no device attached.
2. A full `BOLT_NYC` run over ≥ 20 routes produces ≥ 95% complete screenshot
   sets and a `ZZ_NYC_<DATE>.csv` with valid `price`, `dist`, `trip` values.
3. A failing app (e.g. logged out) aborts the run within
   `MAX_FAIL_THRESHOLD` routes and sends a failure notification.
4. `--analyse` on a second machine reproduces the same CSV from the
   screenshots directory alone.
