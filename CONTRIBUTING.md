# Contributing

Thanks for taking a look. This project automates third-party apps through their
UI, so contributors are expected to run changes against a real device before
opening a pull request.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                           # package + pytest + ruff
pip install -e ".[easyocr]"                       # optional: one OCR engine
pre-commit install                                # optional but recommended
cp config.example.yaml config.yaml                # never commit this file
pytest                                            # 20 tests, no device needed
```

`config.yaml`, `credentials.json`, `token.json` and everything under
`workspace/` are git-ignored. Keep it that way — if you paste a log, strip
device serials and e-mail addresses.

## Definition of done

A change is ready when **all** of these hold:

1. `pytest` passes and new logic comes with a test (see `tests/` for the style).
2. `ruff check --select E9,F src tests examples` is clean.
3. Driver changes were exercised on a device; note the **app version** in the PR.
4. User-visible behaviour is documented: `README.md` for usage, `docs/` for
   design or process, `CHANGELOG.md` under `[Unreleased]`.
5. No secrets, serials or personal paths in the diff.

CI (`.github/workflows/ci.yml`) enforces 1–2 on Python 3.9 and 3.12.

## Adding an app driver

1. Add the resource-id prefix to `ID_PREFIXES` in `src/appautomation/apps/ui_resource.py`.
2. Subclass `App` in `src/appautomation/apps/<app>.py`, set `package`,
   `activity`, `required_suffixes`, implement `get_info()`.
3. Register it in `apps/__init__.py -> APP_REGISTRY`.
4. Map a task key to it in `constants.py -> TASK_APPS`, and add an entry to
   `NO_ANALYSIS_TASKS` if the screenshots are not parsed.
5. Add a crop box per suffix to `constants.py -> SCREEN_PROFILES` if the OCR
   stage consumes it.
6. Extend the device checklist in `docs/TEST_PLAN.md` §5.

Keep flows tolerant: optional dialogs are `if rh.exists(...)`, unstable
coordinate taps carry a comment explaining what is being tapped, and every
lookup goes through `UiResource` so it is logged.

## Adding a city

Add the code to `CITY_NAMES` (and `CITY_STATES` / `CITY_COUNTRIES` when
relevant) in `constants.py`, plus a `routes/<CITY>.csv` with `id,src,dst`
columns. Schedule tasks (`TIME_<CITY>`) also need `hour,minute`.

## Reporting problems

Use the issue templates. For capture bugs, include the last ~30 log lines and
the app version; for OCR bugs, attach a cropped screenshot if you can — it is
usually the fastest way to see whether the profile or the parser is wrong.

## Commit style

Short imperative subject (`Add inDrive driver`, `Fix Google Maps alt-route
detection`), body explaining *why* when the change is not obvious. Keep
unrelated refactors out of functional commits.
