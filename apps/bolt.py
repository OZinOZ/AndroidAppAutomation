"""Bolt capture module (real-world example).

A production capture module for Bolt, kept as a worked example of a
non-trivial flow: pick-up/drop-off entry with coordinate fallbacks, optional
confirmation taps, and two screenshots (fare list ``B`` and fare detail
``BI``).

Resource-id namespace: ``ee.mtakso.client:id/`` is registered in
``config.yaml -> selector_prefixes`` under the ``BOLT`` key, so modules
reference only the short id (e.g. ``rh.click(idx='confirm_button')``).
"""
import logging
import time

from core.app import App
from core.uiresource import UiResource


class Bolt(App):
    app_type = 'BOLT'
    package = 'ee.mtakso.client'
    activity = '.activity.SplashHomeActivity'
    # 'B' = fare list, 'BI' = fare detail of the selected tier
    suffixes = ['B', 'BI']

    def __init__(self, dev, route: int, pickup: str, destination: str, city: str,
                 date: str, output: str, selection: str, present: str):
        super(Bolt, self).__init__(dev, route, pickup, destination, city,
                                   date, output, present)
        self.selection = selection

    def confirm_if_present(self, rh: UiResource, idx: str, settle: int = 2):
        """Tap an optional confirmation button, if the dialog shows one."""
        if rh.exists(idx=idx):
            rh.click(idx=idx)
            time.sleep(settle)

    def get_info(self) -> bool:
        logging.info('BOLT START')
        self.dev.app_start(self.package, self.activity, wait=True, stop=True)
        rh = UiResource(self.dev, self.app_type)

        # Tap the address bar ("Where to?" container)
        if not rh.wait(idx='textContainer'):
            logging.error('BOLT: textContainer not found')
            return False
        rh.click(idx='textContainer')
        time.sleep(1)

        # Pickup: the map layout has no stable ids, so tap by relative
        # coordinates, then type and accept the first suggestion
        rh.dev.click(0.3, 0.125)
        if not rh.input(idx='primaryInput', content=self.src):
            logging.error('BOLT: pickup input not found')
            return False
        time.sleep(3)
        rh.dev.click(0.4, 0.25)
        time.sleep(2)
        self.confirm_if_present(rh, 'confirm_button')

        # Destination
        if not rh.text_operation('Dropoff location', 'exists', 'click'):
            logging.error('BOLT: Dropoff location not found')
            return False
        time.sleep(1)
        self.dev(focused=True).set_text(self.dst)
        time.sleep(3)
        rh.dev.click(0.4, 0.25)
        time.sleep(2)
        self.confirm_if_present(rh, 'confirm_button')

        # Optional promo / info dialog over the fare list
        self.confirm_if_present(rh, 'closeButtonImage', settle=1)

        super(Bolt, self).screenshot('B')

        # Open the fare detail of the selected service tier
        if not rh.text_click('Bolt'):
            logging.error('BOLT: Bolt not found')
            return False
        time.sleep(1)
        if not rh.text_click('Fare'):
            logging.error('BOLT: Fare not found')
            return False

        super(Bolt, self).screenshot('BI')

        logging.info('BOLT FINISH')
        return True
