"""Bolt driver: enters pickup / drop-off and captures the fare screens."""

from __future__ import annotations

import logging
import time

from .base import App
from .ui_resource import UiResource

logger = logging.getLogger(__name__)


class Bolt(App):
    package = "ee.mtakso.client"
    activity = ".activity.SplashHomeActivity"
    required_suffixes = ("B", "BI")

    def get_info(self) -> bool:
        logger.info("BOLT START")
        self.dev.app_start(self.package, self.activity, wait=True, stop=True)
        rh = UiResource(self.dev, "BOLT")

        # Open the pickup editor
        if not rh.wait(idx="textContainer"):
            logger.error("BOLT: textContainer not found")
            return False
        rh.click(idx="textContainer")
        time.sleep(1)

        # Pickup address (relative coordinates: tap the pickup field)
        rh.dev.click(0.3, 0.125)
        rh.input(path=f'//*[@resource-id="{self.package}:id/primaryInput"]/android.widget.EditText[1]',
                 content=self.src)
        time.sleep(3)
        rh.dev.click(0.4, 0.25)  # first suggestion
        time.sleep(2)
        self._confirm(rh)

        # Destination address
        if not rh.text_operation("Dropoff location", "exists", "click"):
            logger.error("BOLT: Dropoff location not found")
            return False
        time.sleep(1)
        self.dev(focused=True).set_text(self.dst)
        time.sleep(3)
        rh.dev.click(0.4, 0.25)  # first suggestion
        time.sleep(2)
        self._confirm(rh)

        if rh.exists(idx="closeButtonImage"):
            rh.click(idx="closeButtonImage")
        time.sleep(1)

        self.screenshot("B")  # ride options overview

        if not rh.text_click("Bolt"):
            logger.error("BOLT: Bolt not found")
            return False
        time.sleep(1)
        if not rh.text_click("Fare"):
            logger.error("BOLT: Fare not found")
            return False

        self.screenshot("BI")  # fare breakdown

        logger.info("BOLT FINISH")
        return True

    @staticmethod
    def _confirm(rh: UiResource) -> None:
        """Press the optional "confirm" button and wait for the screen to settle."""
        if rh.exists(idx="confirm_button"):
            rh.click(idx="confirm_button")
        time.sleep(2)
