"""Orchestration: connect to the phone, record every route, analyse the result."""

from __future__ import annotations

import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from uiautomator2 import Device

from .apps import APP_REGISTRY, AppNotReadyError
from .config import Config
from .constants import MAX_FAIL_THRESHOLD, NO_ANALYSIS_TASKS, TASK_APPS
from .naming import (
    address_adapt, get_city_path, get_task_key, screenshot_exists,
)
from .notify import send_email
from .routes import Route, read_routes, select_routes

logger = logging.getLogger(__name__)

#: Sub folders of ``screenshots/`` selected by a task name token.
TASK_SUBDIRS = {"TIME": "time"}


@dataclass
class RunParams:
    """Everything that identifies one run."""
    config: Config
    phone: str          # alias from config.yaml (lower case)
    task: str           # e.g. ``BOLT_NYC``, ``NYC``, ``TIME_NYC``
    date: str           # label used in file names, e.g. ``0906``
    start: int
    end: int
    partial: bool = False
    capture_only: bool = False

    @property
    def task_key(self) -> str:
        return get_task_key(self.task)

    @property
    def city_route(self) -> str:
        """Route file name without app prefix."""
        return get_city_path(self.task)

    @property
    def apps(self) -> List[str]:
        return TASK_APPS[self.task_key]

    @property
    def screenshot_dir(self) -> str:
        """``<work_base>/screenshots[/time]/<date>_<city>_<phone>``."""
        parts = self.task.split("_")
        sub = TASK_SUBDIRS.get(parts[0]) or TASK_SUBDIRS.get(parts[-1]) or ""
        name = "_".join([self.date, self.city_route, self.phone])
        return str(Path(self.config.work_base, "screenshots", sub, name))


# --------------------------------------------------------------------------- #
# Recording
# --------------------------------------------------------------------------- #
def _run_app_once(app) -> bool:
    """Run ``app.get_info()`` and convert unexpected errors into ``False``."""
    try:
        return app.get_info()
    except AppNotReadyError:
        raise
    except Exception as exc:  # noqa: BLE001 - one bad route must not stop the run
        logger.error("Error: %s", exc)
        return False


def record_route(dev: Device, row: Route, params: RunParams, retry: bool = True) -> bool:
    """Drive every app of the task for one route; retry a failed app once.

    Raises:
        AppNotReadyError: an app cannot be used at all (abort the run).
    """
    logger.info("Start to record %s", row)
    for app_name in params.apps:
        app = APP_REGISTRY[app_name](
            dev, int(row["id"]),
            address_adapt(str(row["src"]), params.task),
            address_adapt(str(row["dst"]), params.task),
            params.city_route, params.date, params.screenshot_dir,
        )
        ok = _run_app_once(app)
        if not ok and retry:
            logger.error("RETRY record: %s", row)
            ok = _run_app_once(app)
        if not ok:
            logger.error("FAILED AT %s, skip this row", app_name)
            return False
    return True


def _record_scheduled(dev: Device, routes: List[Route], params: RunParams) -> None:
    """Wait for each route's ``hour``/``minute`` and record it at that time."""
    while routes:
        time.sleep(2)
        now = datetime.now()
        for row in routes[:]:
            hour, minute = int(row["hour"]), int(row["minute"])
            if hour == now.hour and minute == now.minute:
                record_route(dev, row, params)
                routes.remove(row)
            elif (hour, minute) < (now.hour, now.minute):   # missed slot
                routes.remove(row)


def _record_sequential(dev: Device, routes: List[Route], params: RunParams,
                       fail) -> None:
    """Record all routes one after another; abort after too many failures."""
    failed = 0
    for row in routes:
        try:
            if not record_route(dev, row, params):
                failed += 1
                if failed >= MAX_FAIL_THRESHOLD:
                    fail("FAILED too many times!!")
        except AppNotReadyError:
            fail("FAIL to start APP!!")
        if params.partial:
            time.sleep(random.randint(1, 10))   # be gentle when re-checking a few routes

    # Re-do routes whose screenshots are incomplete
    suffixes = [s for name in params.apps for s in APP_REGISTRY[name].required_suffixes]
    for row in routes:
        if not all(screenshot_exists(params.screenshot_dir, params.city_route, params.date,
                                     int(row["id"]), s) for s in suffixes):
            logger.info("Row %s record not successful, redo it", row)
            try:
                record_route(dev, row, params)
            except AppNotReadyError:
                fail("FAIL to start APP!!")


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def analyse(params: RunParams) -> Optional[str]:
    """OCR the screenshots of the run into a CSV; returns its path (or ``None``)."""
    if params.task_key in NO_ANALYSIS_TASKS:
        logger.info("Analysis is not available for task '%s'", params.task)
        return None

    from .analysis import ScreenshotAnalyser, ScreenshotParser, create_engine

    cfg = params.config
    started = datetime.now()
    engine = create_engine(cfg.ocr_engine, cfg.ocr_gpu, cfg.tesseract_cmd)
    parser = ScreenshotParser(engine, cfg.phone(params.phone).profile)
    csv_path = ScreenshotAnalyser(parser, cfg.work_base, params.city_route, params.date,
                                  params.screenshot_dir, params.phone).run()
    print(f"Finish analysing {params.date} {params.phone} {params.task}, "
          f"time used: {datetime.now() - started}")
    return csv_path


# --------------------------------------------------------------------------- #
# Entry point of a run
# --------------------------------------------------------------------------- #
def setup_logging(params: RunParams) -> None:
    log_dir = Path(params.config.work_base, "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{params.date}_{params.task}_{params.phone}.log"
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[logging.FileHandler(log_file, mode="w", encoding="utf-8"),
                  logging.StreamHandler()],
    )


def run(params: RunParams) -> None:
    """Capture screenshots for the selected routes and analyse them."""
    from . import device

    setup_logging(params)
    cfg = params.config
    tag = ", ".join([params.date, params.task, params.phone])
    dev: Optional[Device] = None

    def finish(title: str, ok: bool) -> None:
        """Release the phone, notify, and exit the process."""
        if dev is not None:
            dev.reset_uiautomator()
            dev.screen_off()
        body = ", ".join([("OK" if ok else "FAIL"), tag])
        (logger.info if ok else logger.error)("%s %s", title, body)
        send_email(cfg.email, title, body)
        sys.exit(0 if ok else 1)

    routes = select_routes(read_routes(cfg.work_base, params.city_route),
                           params.start, params.end, params.partial, cfg.partial_routes)

    dev = device.connect(cfg.phone(params.phone).serial, cfg.adb_path)
    if dev is None:
        finish("FAILED to connect!!", ok=False)

    os.makedirs(params.screenshot_dir, exist_ok=True)
    device.wake_and_unlock(dev)

    if params.task_key == "TIME":
        _record_scheduled(dev, routes, params)
    else:
        _record_sequential(dev, routes, params, lambda msg: finish(msg, ok=False))

    if not params.capture_only:
        analyse(params)

    finish("Successfully finished.", ok=True)
