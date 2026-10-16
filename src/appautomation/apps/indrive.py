"""inDrive driver: enters pickup / drop-off and captures the offer screen."""

from __future__ import annotations

import logging
import time

from .base import App
from .ui_resource import UiResource

logger = logging.getLogger(__name__)


class InDrive(App):
    package = "sinet.startup.inDriver"
    activity = ".ui.splash.SplashActivity"
    required_suffixes = ("IN",)

    def get_info(self) -> bool:
        logger.info("INDRIVE START")
        self.dev.app_start(self.package, self.activity, stop=True)

        rh = UiResource(self.dev, "INDRIVE")
        time.sleep(5)

        # The app may ask whether the detected location is wrong
        if self.dev(resourceId="android:id/text1", text="NO").wait():
            self.dev(resourceId="android:id/text1", text="NO").click()

        self._enter_address(rh, "from", self.src)
        self._enter_address(rh, "to", self.dst)

        time.sleep(2)
        self.screenshot("IN")

        logger.info("INDRIVE FINISH")
        return True

    def _enter_address(self, rh: UiResource, field: str, address: str) -> None:
        """Open the ``from`` / ``to`` field, type ``address`` and pick the first suggestion."""
        field_id = f"form_multilineellipsizetextview_{field}"
        if rh.wait(idx=field_id):
            rh.click_only(idx=field_id)

        if rh.wait(idx="address_edittext"):
            rh.input_only(idx="address_edittext", content=address)
        time.sleep(2)
        self.dev.click(0.438, 0.249)  # first suggestion
