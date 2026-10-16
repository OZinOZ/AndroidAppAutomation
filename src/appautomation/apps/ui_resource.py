"""Thin helper layer over :mod:`uiautomator2` used by every app driver.

It adds waiting, retrying (double clicks) and logging around the raw
``Device`` API so that app scripts read like a list of user actions.
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple

import uiautomator2 as u2
from uiautomator2 import Device

logger = logging.getLogger(__name__)

#: Per-app prefix of Android resource ids (used by ``idx=`` arguments).
ID_PREFIXES = {
    "GOOGLE": "@com.google.android.apps.maps:id/",
    "BOLT": "ee.mtakso.client:id/",
    "INDRIVE": "sinet.startup.inDriver:id/",
}

#: Per-app xpath template to find a text field by its content description.
TEXT_XPATHS = {
    "GOOGLE": "//android.widget.EditText[@content-desc='%s']/android.widget.TextView",
}


class UiResource:
    """Wait / click / input primitives bound to one device and one app."""

    def __init__(self, dev: Device, app_type: str, delay: float = 2, max_wait: int = 5):
        self.dev = dev
        self.app = app_type
        self.delay = delay          # seconds between two polls
        self.max_wait = max_wait    # number of polls before giving up

    # ------------------------------------------------------------------ #
    # xpath helpers
    # ------------------------------------------------------------------ #
    def get_xpath(self, idx: str = "", text: str = "", path: str = "") -> str:
        """Build an xpath from a resource id, a text label, or a raw path."""
        if idx:
            return ID_PREFIXES[self.app] + idx
        if text:
            return TEXT_XPATHS[self.app] % text
        return path

    def _resolve(self, path_type: str, item: str) -> str:
        if path_type == "id":
            return ID_PREFIXES[self.app] + item
        if path_type == "text":
            return TEXT_XPATHS[self.app] % item
        return item

    # ------------------------------------------------------------------ #
    # existence / waiting
    # ------------------------------------------------------------------ #
    def exists(self, idx: str = "", text: str = "", path: str = "") -> bool:
        xpath = self.get_xpath(idx, text, path)
        logger.info("%s CHECK EXIST %s", self.app, xpath)
        return self.dev.xpath(xpath).exists

    def exists_multi(self, path_type: str, paths: List[str]) -> Tuple[bool, str]:
        """Return ``(True, item)`` for the first item that is on screen."""
        logger.info("%s CHECK EXISTS MULTI %s", self.app, paths)
        for item in paths:
            if self.dev.xpath(self._resolve(path_type, item)).exists:
                return True, item
        return False, ""

    def wait_xpath(self, xpath: str) -> bool:
        """Poll until ``xpath`` appears (``max_wait`` * ``delay`` seconds)."""
        for i in range(self.max_wait):
            time.sleep(self.delay)
            if self.dev.xpath(xpath).exists:
                logger.info("%s WAIT exist %s loop %d", self.app, xpath, i)
                return True
        logger.error("%s WAIT NOT exist %s %d", self.app, xpath, self.max_wait)
        return False

    def wait(self, idx: str = "", text: str = "", path: str = "") -> bool:
        return self.wait_xpath(self.get_xpath(idx, text, path))

    def wait_multi(self, path_type: str, paths: List[str]) -> Tuple[bool, str]:
        """Wait until any of ``paths`` shows up; return ``(found, item)``."""
        for _ in range(self.max_wait):
            time.sleep(self.delay)
            for item in paths:
                if self.dev.xpath(self._resolve(path_type, item)).exists:
                    logger.info("%s WAIT MULTI found: %s", self.app, item)
                    return True, item
        logger.error("%s WAIT MULTI NOTHING found", self.app)
        return False, ""

    def wait_multi_input(self, path_type: str, paths: List[str], fill: str) -> bool:
        logger.info("%s WAIT MULTI INPUT %s %s", self.app, paths, fill)
        found, item = self.wait_multi(path_type, paths)
        if found:
            self.input_only(idx=item, content=fill)
            return True
        logger.error("%s DOES NOT SHOW", paths)
        return False

    def wait_multi_clickitem(self, path_type: str, paths: List[str]) -> bool:
        """Wait for any of ``paths`` and click the first match of a list."""
        logger.info("%s WAIT MULTI CLICK %s", self.app, paths)
        found, item = self.wait_multi(path_type, paths)
        if found:
            self.click_item(idx=item)
            return True
        logger.error("%s DOES NOT SHOW", paths)
        return False

    def wait_multi_click(self, path_type: str, paths: List[str]) -> bool:
        """Wait for any of ``paths`` and click it."""
        logger.info("%s WAIT MULTI CLICK %s", self.app, paths)
        found, item = self.wait_multi(path_type, paths)
        if not found:
            logger.error("%s DOES NOT SHOW", paths)
            return False
        if path_type == "text":
            self.click_only(text=item)
        else:
            self.click_only(idx=item)
        return True

    # ------------------------------------------------------------------ #
    # click / input
    # ------------------------------------------------------------------ #
    def click_only(self, idx: str = "", text: str = "", path: str = "") -> None:
        xpath = self.get_xpath(idx, text, path)
        try:
            self.dev.xpath(xpath).click()
        except u2.exceptions.XPathElementNotFoundError:
            logger.error("%s %s XPathElementNotFoundError", self.app, xpath)

    def click(self, idx: str = "", text: str = "", path: str = "") -> None:
        """Wait for the element, then click it."""
        xpath = self.get_xpath(idx, text, path)
        logger.info("%s CLICK %s", self.app, xpath)
        if self.wait_xpath(xpath):
            self.click_only(idx, text, path)
        else:
            logger.error("%s %s ERROR NOT FOUND", self.app, xpath)

    def input_only(self, idx: str = "", text: str = "", path: str = "", content: str = "") -> None:
        """Focus the element (clicked twice for reliability) and type ``content``."""
        xpath = self.get_xpath(idx, text, path)
        self.dev.xpath(xpath).click()
        time.sleep(1)  # let the first click take effect
        self.dev.xpath(xpath).click()
        self.dev(focused=True).set_text(content)

    def input(self, idx: str = "", text: str = "", path: str = "", content: str = "") -> bool:
        """Wait for the element, then type ``content`` into it."""
        xpath = self.get_xpath(idx, text, path)
        logger.info("%s INPUT %s%s%s", self.app, idx, text, path)
        if self.wait_xpath(xpath):
            self.input_only(idx, text, path, content)
            return True
        logger.error("%s %s ERROR NOT FOUND", self.app, xpath)
        return False

    def click_list(self, idx: str = "", text: str = "", path: str = "") -> bool:
        """Click the first element of a result list (after a short pause)."""
        xpath = self.get_xpath(idx, text, path)
        logger.info("%s CLICK LIST %s%s%s", self.app, idx, text, path)
        time.sleep(3)
        if self.dev.xpath(xpath).exists:
            logger.info("%s found and click %s", self.app, xpath)
            self.dev.xpath(xpath).all()[0].click()
            return True
        logger.error("%s NOT FOUND %s", self.app, xpath)
        return False

    def click_item(self, idx: str = "", text: str = "", path: str = "") -> None:
        """Click the first element matching the selector."""
        xpath = self.get_xpath(idx, text, path)
        logger.info("%s CLICK ITEM %s%s%s", self.app, idx, text, path)
        self.dev.xpath(xpath).all()[0].click()

    def click_sleep(self, pre_sleep: float, x: float, y: float, sleep: float) -> None:
        """Click a relative screen point with optional sleeps around it."""
        if pre_sleep:
            time.sleep(pre_sleep)
        self.dev.click(x, y)
        if sleep:
            time.sleep(sleep)

    def click_sleep_multi(self, pre_sleep: float, x: float, y: float, sleep: float, count: int) -> None:
        for _ in range(count):
            self.click_sleep(pre_sleep, x, y, sleep)

    # ------------------------------------------------------------------ #
    # resource-id / text / description operations
    # ------------------------------------------------------------------ #
    def id_operation(self, idx: str = "", exist: str = "", click: str = "", fill: str = "") -> bool:
        """Optionally check existence, click (twice) and fill a resource id."""
        resource_id = ID_PREFIXES[self.app][1:] + idx
        element = self.dev(resourceId=resource_id)
        if exist == "exist" and not element.exists():
            logger.error("%s %s NOT exist", self.app, resource_id)
            return False

        if click == "click" and element.exists():
            logger.info("%s %s click", self.app, idx)
            element.click()
            time.sleep(1)
            if element.exists():
                element.click()

        if fill and element.exists():
            logger.info("%s %s input %s", self.app, idx, fill)
            self.dev(focused=True).set_text(fill)
        return True

    def text_wait(self, txt: str = "") -> bool:
        """Poll until a view with exactly this text is visible."""
        for i in range(self.max_wait):
            time.sleep(self.delay)
            if self.dev(text=txt).exists:
                logger.info("%s WAIT found %s %d", self.app, txt, i)
                return True
        logger.info("%s WAIT not found %s", self.app, txt)
        return False

    def text_wait_sleep(self, txt: str = "", sleep: float = 0) -> None:
        logger.info("%s wait for %s", self.app, txt)
        if sleep > 0:
            time.sleep(sleep)
        self.dev(text=txt).wait()
        if sleep > 0:
            time.sleep(sleep)

    def text_operation(self, txt: str = "", exist: str = "", click: str = "") -> bool:
        """Check that ``txt`` is on screen and/or click it (twice, for reliability)."""
        element = self.dev(text=txt)
        if exist == "exist" and not element.exists():
            logger.error("%s %s NOT exist", self.app, txt)
            return False

        if click == "click":
            if not element.exists():
                logger.error("%s %s NOT FOUND", self.app, txt)
                return False
            logger.info("%s %s click", self.app, txt)
            element.click()
            time.sleep(1)  # make the click consistent: click twice
            if element.exists():
                element.click()
        return True

    def text_click(self, txt: str = "") -> bool:
        """Click once on the view with this text."""
        if not self.dev(text=txt).exists():
            logger.error("%s %s NOT exist", self.app, txt)
            return False
        logger.info("%s %s click", self.app, txt)
        self.dev(text=txt).click()
        return True

    def text_operation_wait(self, text: str = "", exist: str = "", click: str = "", sleep: float = 0) -> bool:
        self.text_wait(txt=text)
        return self.text_operation_sleep(text, exist, click, sleep)

    def text_operation_sleep(self, txt: str = "", exist: str = "", click: str = "", sleep: float = 0) -> bool:
        if not self.text_operation(txt, exist, click):
            return False
        if sleep > 0:
            time.sleep(sleep)
        return True

    def get_text_bottom(self, txt: str = "") -> int:
        """Bottom pixel of the view with this text, or 0 when missing."""
        if self.dev(text=txt).exists():
            return self.dev(text=txt).bounds()[3]
        return 0

    def get_text_top(self, txt: str = "") -> int:
        """Top pixel of the view with this text, or 0 when missing."""
        if self.dev(text=txt).exists():
            return self.dev(text=txt).bounds()[1]
        return 0

    def desc_operation(self, desc: str = "") -> bool:
        """Click the first view whose content description starts with ``desc``."""
        matches = self.dev(descriptionStartsWith=desc)
        if len(matches) > 0:
            self.dev(description=matches[0].info["contentDescription"]).click()
            return True
        return False

    # ------------------------------------------------------------------ #
    # gestures / geometry
    # ------------------------------------------------------------------ #
    def swipes(self, direction: str, scale: float, sleeps: float, times: int) -> bool:
        """Swipe ``up`` / ``down`` (``scale`` > 0) or press ``back`` repeatedly."""
        for _ in range(times):
            if direction in ("up", "down") and scale:
                self.dev.swipe_ext(direction, scale=scale)
            elif direction == "back":
                self.dev.press("back")
            if sleeps:
                time.sleep(sleeps)
        return True

    def xpath_operation(self, path_name: str = "", exist: str = "", click: str = "") -> bool:
        if exist == "exist":
            self.dev.xpath(path_name).wait()
            if not self.dev.xpath(path_name).exists:
                logger.error("%s %s NOT exist", self.app, path_name)
                return False
            logger.info("%s %s found", self.app, path_name)

        if click == "click":
            logger.info("%s %s click", self.app, path_name)
            self.dev.xpath(path_name).click()
            time.sleep(3)
            if self.dev.xpath(path_name).exists:
                self.dev.xpath(path_name).click()
        return True

    def click_obj_middle(self, pre_wait: float = 0, xpath: str = "", post_wait: float = 0) -> bool:
        """Click the centre of the element found by ``xpath``."""
        if pre_wait > 0:
            time.sleep(pre_wait)
        element = self.dev.xpath(xpath)
        if not element.exists:
            logger.error("%s %s NOT exist", self.app, xpath)
            return False

        left, top, right, bottom = element.bounds
        center = ((left + right) // 2, (top + bottom) // 2)
        logger.info("%s %s found click middle point: %s", self.app, xpath, center)
        self.dev.click(*center)
        if post_wait > 0:
            time.sleep(post_wait)
        return True

    def swipe_objects(self, from_path: str = "", to_path: str = "") -> bool:
        """Drag the centre of one element to the top edge of another."""
        source, target = self.dev.xpath(from_path), self.dev.xpath(to_path)
        if not (source.exists and target.exists):
            logger.error("%s %s %s NOT both exist", self.app, from_path, to_path)
            return False
        sx1, sy1, sx2, sy2 = source.bounds
        tx1, ty1, tx2, _ = target.bounds
        self.dev.swipe((sx1 + sx2) / 2, (sy1 + sy2) / 2, (tx1 + tx2) / 2, ty1)
        return True
