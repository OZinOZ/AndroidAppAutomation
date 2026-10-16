"""Android device connection helpers."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Optional

import uiautomator2 as u2
from uiautomator2 import Device

logger = logging.getLogger(__name__)

RETRY_WAIT_SECONDS = 30
WAIT_TIMEOUT_SECONDS = 8


def connect(serial: str, adb_path: str = "adb") -> Optional[Device]:
    """Connect to the phone with ``serial``; return ``None`` when it fails.

    A stale ``atx-agent`` on the phone is stopped first so that
    uiautomator2 starts a fresh one. The connection is retried once.
    """
    stop_cmd = [adb_path, "-s", serial, "shell", "/data/local/tmp/atx-agent", "server", "-d", "--stop"]
    try:
        subprocess.check_call(stop_cmd)
    except subprocess.CalledProcessError as exc:
        logger.error("atx agent command failed with return code %d: %s", exc.returncode, exc)
    except OSError as exc:  # adb missing, not executable, ...
        logger.error("Unexpected error while stopping atx agent: %s", exc)

    time.sleep(3)
    device = _try_connect(serial)
    if device is None:
        logger.error("Unable to connect, wait for %d seconds", RETRY_WAIT_SECONDS)
        time.sleep(RETRY_WAIT_SECONDS)
        device = _try_connect(serial)
    if device is None:
        logger.error("Unable to connect, exit")
        return None

    logger.info(json.dumps(device.device_info))
    logger.info(json.dumps(device.info))
    device.settings["wait_timeout"] = WAIT_TIMEOUT_SECONDS
    return device


def _try_connect(serial: str) -> Optional[Device]:
    try:
        return u2.connect(serial)
    except Exception:  # noqa: BLE001 - uiautomator2 raises many exception types
        return None


def wake_and_unlock(dev: Device) -> None:
    """Turn the screen on, unlock it (swipe, no PIN) and return to the home screen."""
    logger.info("Connect to device")
    dev.screen_on()
    time.sleep(0.5)
    dev.unlock()
    time.sleep(0.5)
    dev.swipe_ext("up", scale=0.8)
    time.sleep(0.5)
    dev.swipe(0.5, 0.9, 0.5, 0.1, 0.5)
    time.sleep(0.5)
