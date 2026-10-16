# AndroidAppAutomation

A modular Python framework for capturing and analysing app screen data on
Android devices: it drives apps with `uiautomator2`, captures screenshots
along configurable routes, extracts structured data with pluggable OCR
engines (EasyOCR / PaddleOCR / Tesseract), and writes tidy CSV output.

Originally built for large-scale fare monitoring across ride-hailing and
delivery apps; the platform-specific capture modules are intentionally kept
out of this public repository, which ships the reusable framework plus one
generic example app.

## Architecture

```
main.py                 CLI entry: config -> routes -> capture -> analyse
|
|-- core/
|   |-- config.py       loads config.yaml (git-ignored; see config.example.yaml)
|   |-- app.py          App base class: identity, screenshots, naming
|   |-- uiresource.py   UiResource: selector lookup, waits, clicks, swipes
|   |-- common.py       city metadata, price parsing, route loading
|   |-- notify.py       optional e-mail notifications (env-var driven)
|   |-- phone.py        per-device analysis orchestration
|   |-- file_parser.py  screenshot -> OCR engine dispatch
|   `-- file_handle.py  CSV writer
|
|-- ocr/                pluggable OCR backends
|   |-- img_ocr.py      shared base: cropping, binarisation, fare extraction
|   |-- img_easy.py     EasyOCR backend (preferred)
|   |-- img_paddle.py   PaddleOCR backend
|   `-- img_tesser.py   Tesseract backend (fallback)
|
`-- apps/
    |-- __init__.py     APP_REGISTRY
    `-- demo_ride.py    generic example capture module
```

## How it works

1. **Capture** - for each row of a route file (`id, src, dst`) the runner
   connects to an Android device over ADB, unlocks it, launches the target
   app, enters pickup and destination, and screenshots the fare list and fare
   detail pages. Files are named `<CITY><DATE><ROUTE:03d><TYPE>.png`, where
   `TYPE` is a screenshot-type code (`D` = fare list, `DI` = fare detail,
   `G` = map reference, ...).
2. **Analyse** - each screenshot is cropped to a region defined in
   `config.yaml -> crop_ranges`, binarised, and parsed by the best available
   OCR engine. Extracted fields (price, surge, fare components, distance,
   trip time) plus an address-validation confidence score are written to CSV.

## Requirements

- Python 3.8+
- An Android device connected via ADB with developer options enabled
- At least one OCR engine (see `requirements.txt`; Tesseract needs its binary)

## Quick start

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # then edit devices / selector prefixes
```

Route files are CSVs with columns `id, src, dst`:

```csv
id,src,dst
1,Central Station,Harbour Bridge Lookout
2,City Library,Airport Terminal 1
```

Capture and analyse routes 1-3 in city `SAMPLE` with device `model_a`:

```bash
python main.py model_a SAMPLE 0000 1 3
```

Analyse existing screenshots without capturing:

```bash
python main.py model_a SAMPLE 0000 1 3 --analyse
```

## Configuration

Copy `config.example.yaml` to `config.yaml`. `config.yaml` is git-ignored -
never commit device serials, credentials or API keys.

| Key | Purpose |
|---|---|
| `devices` | phone alias -> ADB serial |
| `selector_prefixes` | per-app resource-id namespace used by `UiResource` |
| `text_xpath` | optional per-app xpath templates for text lookups |
| `crop_ranges` | per-device OCR crop regions, `[top, bottom, left, right]` |
| `morph_kernel_size` | per-device binarisation kernel for Tesseract |
| `city_map` / `city_state` | address qualification metadata |
| `default_selections` | service-tier text offered per app in `--selection` mode |

## Adding a new app

1. Dump the app UI (`adb shell uiautomator dump`) and add its resource-id
   prefix to `selector_prefixes`.
2. Subclass `core.app.App`, set `app_type` / `package` / `activity` /
   `suffixes`, and implement `get_info()`. See `apps/demo_ride.py`.
3. Register the class in `apps/__init__.py -> APP_REGISTRY`.

The example module documents the expected flow: launch, dismiss popups,
enter route, capture, and report success so the runner can retry.

## OCR calibration

Crop regions are device-specific. Capture one screenshot per type, note the
pixel bounds of the interesting areas, and fill them in under
`crop_ranges[<device alias>]`. Keys must match the screenshot-type codes
your app modules emit (e.g. `D`, `DI`, `DS` for the surge banner).

## Legal note

This project is provided for educational and research purposes. Automating an
application may violate that application's terms of service; you are
responsible for complying with the terms of any service you interact with,
and for respecting applicable data-protection law. No credentials, device
identifiers or proprietary app definitions are included in this repository.

## License

GPL-3.0 - see [LICENSE](LICENSE).
