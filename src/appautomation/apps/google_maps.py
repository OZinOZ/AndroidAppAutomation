"""Google Maps driver: captures distance / duration of the best route."""

from __future__ import annotations

import logging
import time
from typing import List

from uiautomator2 import Device

from ..naming import address_origin
from .base import App
from .ui_resource import UiResource

logger = logging.getLogger(__name__)

DIRECTIONS = "Directions"


class Google(App):
    package = "com.google.android.apps.maps"
    activity = "com.google.android.maps.MapsActivity"
    required_suffixes = ("G",)

    #: Content-description prefixes of alternative routes.
    ALTERNATE_PREFIXES = ("Alternate", "Alternative")

    def __init__(self, dev: Device, *args, **kwargs):
        super().__init__(dev, *args, **kwargs)
        self.origin = address_origin(self.dst, self.city)

    def get_info(self) -> bool:
        logger.info("GOOGLE START")
        self.dev.app_start(self.package, self.activity, wait=True, stop=True)
        rh = UiResource(self.dev, "GOOGLE")
        time.sleep(5)

        # A permission pop-up sometimes appears; dismiss it
        rh.text_operation_sleep("While using the app", "", "click", 2)

        if not self._open_search_bar(rh):
            logger.error("GOOGLE error: NO ADDRESS BAR, RESTART")
            return False

        # Destination first, then the start location
        time.sleep(1)
        rh.input(idx="search_omnibox_edit_text", content=self.dst)
        rh.click_list(idx="compass_container")  # first suggestion
        if not self._open_directions(rh):
            return False
        time.sleep(1)
        self._set_start(rh)

        rh.click_list(idx="compass_container")
        time.sleep(3)
        if rh.desc_operation(DIRECTIONS):
            time.sleep(3)

        # A survey pop-up sometimes covers the result
        rh.id_operation("survey_close_button", "", "click", "")

        self.screenshot("G")

        selected = rh.dev(descriptionStartsWith="Selected")
        if len(selected) == 0:
            logger.error("GOOGLE error: NO valid route found")
            return False
        logger.info("GOOGLE route: %s", selected.info["contentDescription"])

        for i, description in enumerate(self._alternative_routes(rh)):
            try:
                logger.info("GOOGLE alternative: %d %s", i, description)
                rh.dev(description=description).click()
                self.screenshot(f"G{i}")
            except Exception:  # noqa: BLE001 - UI flakiness must not abort the run
                logger.info("GOOGLE alternatives %d walk through fail", i)

        logger.info("GOOGLE FINISH")
        return True

    # ------------------------------------------------------------------ #
    @staticmethod
    def _open_search_bar(rh: UiResource) -> bool:
        if rh.exists(idx="search_omnibox_edit_text"):
            rh.click_only(idx="search_omnibox_edit_text")
            return True
        return rh.wait_multi_click("text", ["Search here", "Try petrol stations, ATMs"])

    def _open_directions(self, rh: UiResource) -> bool:
        """Click through the place card until the directions page is open."""
        time.sleep(3)
        if rh.text_operation("More info", "exist", "click"):  # optional button
            time.sleep(1)

        if rh.text_operation(DIRECTIONS, "exist", "click"):
            time.sleep(1)
            rh.desc_operation(DIRECTIONS)  # a place with multiple entrances
            return True

        # The destination is a big area (e.g. an airport)
        if rh.desc_operation(DIRECTIONS):
            time.sleep(1)
        if rh.text_operation(self.origin, "exist", "click"):
            time.sleep(2)
        if not rh.text_operation(DIRECTIONS, "exist", "click"):
            logger.error("GOOGLE CANNOT select destination")
            return False
        return True

    def _set_start(self, rh: UiResource) -> None:
        your_location = '//*[@text="Your location"]'
        choose_start = '//*[@text="Choose start location"]'
        found, item = rh.wait_multi("path", [your_location, choose_start])
        if not found:
            return
        if item == your_location:
            rh.click_only(path=item)
            time.sleep(1)
            rh.input(path=choose_start, content=self.src)
        else:
            rh.input_only(path=item, content=self.src)

    def _alternative_routes(self, rh: UiResource) -> List[str]:
        """Collect unique descriptions of alternative routes ("min" == "minutes")."""
        routes: List[str] = []
        for prefix in self.ALTERNATE_PREFIXES:
            for element in rh.dev(descriptionStartsWith=prefix):
                desc = element.info["contentDescription"]
                if desc in routes or desc.replace("minutes", "min") in routes:
                    continue
                if any(r.replace("minutes", "min") == desc for r in routes):
                    continue
                routes.append(desc)
        return routes
